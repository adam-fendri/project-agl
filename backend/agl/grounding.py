from __future__ import annotations

import re
from decimal import Decimal

from agl.models import (
    Account,
    Bill,
    CandidateFact,
    Correction,
    Evidence,
    Invoice,
    Transaction,
    VendorHistoryEntry,
)
from agl.reconcile import Candidate, find_candidates
from agl.repository import Repository


def build_evidence(txn: Transaction, repo: Repository, customer_id: str) -> Evidence:
    """Assemble the grounded Evidence for one transaction.

    Pulls the chart of accounts, the provided match plus reconciliation candidates with their
    computed facts (amount vs document total, direction, paid/unpaid status), the relevant
    corrections, and vendor history. No duplicate hint reaches the agent: a duplicate is a
    cross-transaction fact the guard resolves from the full set of matches, never a per-call signal.
    """
    accounts = repo.accounts(customer_id)
    invoices = repo.invoices(customer_id)
    bills = repo.bills(customer_id)
    transactions = repo.transactions(customer_id)

    provided = _provided_fact(txn, repo)
    candidates = _candidate_facts(txn, repo, invoices, bills, provided, transactions)
    corrections = _relevant_corrections(txn, repo.corrections(customer_id))
    vendor_history = _vendor_history(txn, transactions, repo)
    known_ids = {i.id for i in invoices} | {b.id for b in bills}
    referenced = referenced_documents(txn, known_ids)

    return Evidence(
        transaction=txn,
        accounts=accounts,
        provided_match=provided,
        candidates=candidates,
        corrections=corrections,
        vendor_history=vendor_history,
        referenced_documents=referenced,
    )


def render_prompt(evidence: Evidence) -> str:
    """Render the Evidence into the user-prompt text the agent reads for its single structured-output call."""
    lines: list[str] = []
    lines.extend(_render_transaction(evidence.transaction))
    lines.append("")
    lines.extend(_render_accounts(evidence.accounts))
    if evidence.referenced_documents:
        lines.append("")
        lines.extend(_render_reference(evidence.referenced_documents))
    lines.append("")
    lines.extend(_render_provided(evidence.transaction, evidence.provided_match))
    lines.append("")
    lines.extend(_render_candidates(evidence.transaction, evidence.candidates))
    lines.append("")
    lines.extend(_render_corrections(evidence.corrections))
    lines.append("")
    lines.extend(_render_vendor_history(evidence.vendor_history))
    return "\n".join(lines)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _distinctive_tokens(text: str) -> set[str]:
    return {token for token in _tokens(text) if len(token) >= 4}


def _raw_string(txn: Transaction) -> str:
    return f"{txn.counterparty} {txn.description}"


def _vendor_matches_raw(vendor: str, raw: str) -> bool:
    vendor_tokens = _distinctive_tokens(vendor)
    if not vendor_tokens:
        return False
    return bool(vendor_tokens & _tokens(raw))


def counterparty_agrees(party: str, txn: Transaction) -> bool:
    """True when the document party shares a distinctive token with the transaction line (counterparty + description)."""
    return _vendor_matches_raw(party, _raw_string(txn))


_DOCUMENT_REFERENCE = re.compile(r"\b(?:INV-\d{4}-\d{3}|B-\d{2})\b")


def referenced_documents(txn: Transaction, known_ids: set[str]) -> list[str]:
    """Our own document ids written literally in the payment remittance, restricted to ids we hold.

    A hard reconciliation signal: the payer quotes our invoice/bill id (``INV-2026-004``, ``B-01``)
    in the bank line. Counterparty-own numbers (``FACTUUR SP-2026-018``) never match our two id shapes.
    """
    found = {ref for ref in _DOCUMENT_REFERENCE.findall(_raw_string(txn)) if ref in known_ids}
    return sorted(found)


def transactions_share_vendor(a: Transaction, b: Transaction) -> bool:
    """True when two transaction lines share a distinctive token, i.e. look like the same vendor."""
    return bool(_distinctive_tokens(_raw_string(a)) & _distinctive_tokens(_raw_string(b)))


def party_of(doc: Invoice | Bill) -> str:
    return doc.client if isinstance(doc, Invoice) else doc.supplier


def _relation(gap: Decimal) -> str:
    if gap == 0:
        return "exact"
    return "short" if gap < 0 else "over"


def _fact_for_documents(txn: Transaction, documents: list[Invoice | Bill]) -> CandidateFact:
    gross = Decimal("0")
    for doc in documents:
        gross += doc.gross
    gap = abs(txn.amount) - gross
    party = (
        party_of(documents[0])
        if len(documents) == 1
        else " + ".join(party_of(d) for d in documents)
    )
    candidate = Candidate(
        document_ids=[d.id for d in documents],
        party=party,
        gross=gross,
        relation=_relation(gap),
        gap=gap,
        is_combination=len(documents) > 1,
    )
    return CandidateFact(candidate=candidate, documents=list(documents))


def _provided_fact(txn: Transaction, repo: Repository) -> CandidateFact | None:
    provided = repo.provided_match(txn.id)
    if provided is None:
        return None
    doc = repo.document(provided.document_id)
    if doc is None:
        return None
    return _fact_for_documents(txn, [doc])


def _candidate_facts(
    txn: Transaction,
    repo: Repository,
    invoices: list[Invoice],
    bills: list[Bill],
    provided: CandidateFact | None,
    transactions: list[Transaction],
) -> list[CandidateFact]:
    closed = _settled_before(txn, repo, transactions, invoices, bills)
    seen: set[frozenset[str]] = set()
    if provided is not None:
        seen.add(frozenset(provided.candidate.document_ids))
    facts: list[CandidateFact] = []
    for candidate in find_candidates(txn, invoices, bills):
        key = frozenset(candidate.document_ids)
        if key in seen or key & closed:
            continue
        documents = [
            doc for did in candidate.document_ids if (doc := repo.document(did)) is not None
        ]
        if not documents:
            continue
        seen.add(key)
        facts.append(CandidateFact(candidate=candidate, documents=documents))
    for fact in _same_counterparty_facts(txn, invoices, bills, seen, closed):
        seen.add(frozenset(fact.candidate.document_ids))
        facts.append(fact)
    return facts


def _settled_before(
    txn: Transaction,
    repo: Repository,
    transactions: list[Transaction],
    invoices: list[Invoice],
    bills: list[Bill],
) -> frozenset[str]:
    """Documents an earlier transaction credibly settled, modelling 'open as of booked_on'.

    An earlier provided match closes its document when the amount is exact, EXCEPT when the
    document has a same-amount sibling and the earlier transaction's counterparty does not
    corroborate it (the collision the provided match may have swapped) — that document stays
    reachable as a candidate for the later transaction.
    """
    closed: set[str] = set()
    for other in transactions:
        if other.id == txn.id or (other.booked_on, other.id) >= (txn.booked_on, txn.id):
            continue
        provided = repo.provided_match(other.id)
        if provided is None:
            continue
        doc = repo.document(provided.document_id)
        if doc is None or abs(other.amount) != doc.gross:
            continue
        if _has_amount_twin(doc, invoices, bills) and not counterparty_agrees(party_of(doc), other):
            continue
        closed.add(doc.id)
    return frozenset(closed)


def _has_amount_twin(doc: Invoice | Bill, invoices: list[Invoice], bills: list[Bill]) -> bool:
    siblings: list[Invoice] | list[Bill] = invoices if isinstance(doc, Invoice) else bills
    return any(other.gross == doc.gross and other.id != doc.id for other in siblings)


def _same_counterparty_facts(
    txn: Transaction,
    invoices: list[Invoice],
    bills: list[Bill],
    seen: set[frozenset[str]],
    closed: frozenset[str],
) -> list[CandidateFact]:
    documents: list[Invoice | Bill] = list(invoices) if txn.amount > 0 else list(bills)
    facts: list[CandidateFact] = []
    for doc in documents:
        if doc.id in closed or frozenset([doc.id]) in seen:
            continue
        if not counterparty_agrees(party_of(doc), txn):
            continue
        facts.append(_fact_for_documents(txn, [doc]))
    return facts


def _relevant_corrections(txn: Transaction, corrections: list[Correction]) -> list[Correction]:
    raw = _raw_string(txn)
    relevant: list[Correction] = []
    for correction in corrections:
        if not correction.vendor.strip():
            relevant.append(correction)
        elif _vendor_matches_raw(correction.vendor, raw):
            relevant.append(correction)
    return relevant


def _vendor_history(
    txn: Transaction,
    transactions: list[Transaction],
    repo: Repository,
) -> list[VendorHistoryEntry]:
    own_tokens = _distinctive_tokens(txn.counterparty)
    if not own_tokens:
        return []
    history: list[VendorHistoryEntry] = []
    for other in transactions:
        if other.id == txn.id:
            continue
        if (other.booked_on, other.id) >= (txn.booked_on, txn.id):
            continue
        if not (own_tokens & _distinctive_tokens(other.counterparty)):
            continue
        provided = repo.provided_match(other.id)
        if provided is None:
            continue
        doc = repo.document(provided.document_id)
        if not isinstance(doc, Bill):
            continue
        history.append(
            VendorHistoryEntry(
                transaction_id=other.id,
                counterparty=other.counterparty,
                account=doc.account,
                amount=other.amount,
                booked_on=other.booked_on,
            )
        )
    return history


def _eur(amount: Decimal) -> str:
    return f"EUR {amount:.2f}"


def _direction(amount: Decimal) -> str:
    return "inflow (money in)" if amount > 0 else "outflow (money out)"


def _render_transaction(txn: Transaction) -> list[str]:
    return [
        "## TRANSACTION",
        f"id: {txn.id}",
        f"booked_on: {txn.booked_on.isoformat()}",
        f"amount: {_eur(txn.amount)} ({_direction(txn.amount)})",
        f"type: {txn.type.value}",
        f"counterparty: {txn.counterparty}",
        f"description: {txn.description}",
    ]


def _render_accounts(accounts: list[Account]) -> list[str]:
    lines = ["## CHART OF ACCOUNTS"]
    for account in accounts:
        lines.append(
            f"{account.number}  {account.name_en} / {account.name_nl}  [rubriek {account.rubriek.value}]"
        )
    return lines


def _gap_phrase(fact: CandidateFact) -> str:
    gap = fact.candidate.gap
    if gap == 0:
        return "amount equals the document total exactly"
    if gap < 0:
        return f"amount is {_eur(abs(gap))} below the document total"
    return f"amount is {_eur(gap)} above the document total"


def _direction_note(txn: Transaction, documents: list[Invoice | Bill]) -> str:
    inflow = txn.amount > 0
    all_invoices = all(isinstance(d, Invoice) for d in documents)
    all_bills = all(isinstance(d, Bill) for d in documents)
    if inflow and all_invoices:
        return "direction fits (incoming payment, issued invoice)"
    if (not inflow) and all_bills:
        return "direction fits (outgoing payment, received bill)"
    return "direction does not fit (payment direction and document type disagree)"


def _counterparty_phrase(txn: Transaction, fact: CandidateFact) -> str:
    if counterparty_agrees(fact.candidate.party, txn):
        return "party appears in the transaction line"
    return "party does not appear in the transaction line"


def _render_fact(txn: Transaction, fact: CandidateFact) -> list[str]:
    candidate = fact.candidate
    header = "+".join(candidate.document_ids) + (
        " (combination)" if candidate.is_combination else ""
    )
    lines = [
        f"- {header}  party: {candidate.party}  total: {_eur(candidate.gross)}",
        f"  {_gap_phrase(fact)}; {_direction_note(txn, fact.documents)}; {_counterparty_phrase(txn, fact)}",
    ]
    for doc in fact.documents:
        lines.append(
            f"  {doc.id}: {party_of(doc)}, gross {_eur(doc.gross)}, status {doc.status.value}"
        )
    return lines


def _render_reference(referenced: list[str]) -> list[str]:
    return [
        "## PAYMENT REFERENCE",
        f"This payment's remittance names document(s): {', '.join(referenced)}",
    ]


def _render_provided(txn: Transaction, provided: CandidateFact | None) -> list[str]:
    lines = ["## SUGGESTED MATCH (the matching system's prior for this transaction)"]
    if provided is None:
        lines.append("- none provided for this transaction")
        return lines
    lines.extend(_render_fact(txn, provided))
    return lines


def _render_candidates(txn: Transaction, candidates: list[CandidateFact]) -> list[str]:
    lines = ["## RECONCILIATION CANDIDATES (other documents whose amount or party fits this transaction)"]
    if not candidates:
        lines.append("- none found")
        return lines
    for fact in candidates:
        lines.extend(_render_fact(txn, fact))
    return lines


def _render_correction(correction: Correction) -> list[str]:
    scope = correction.vendor.strip() or "general"
    parts = [f"- [{scope}]"]
    if correction.corrected_account is not None:
        parts.append(f"account -> {correction.corrected_account}")
    if correction.corrected_match is not None:
        parts.append(f"match rule -> {correction.corrected_match}")
    lines = [" ".join(parts)]
    if correction.note:
        lines.append(f"  note: {correction.note}")
    return lines


def _render_corrections(corrections: list[Correction]) -> list[str]:
    lines = ["## PRIOR CORRECTIONS"]
    if not corrections:
        lines.append("- none on record")
        return lines
    vendor_bound = [c for c in corrections if c.vendor.strip()]
    general = [c for c in corrections if not c.vendor.strip()]
    if vendor_bound:
        lines.append("Vendor-specific conventions (apply when the vendor matches this transaction):")
        for correction in vendor_bound:
            lines.extend(_render_correction(correction))
    if general:
        lines.append("General policies (apply only when the stated condition holds, not to every transaction):")
        for correction in general:
            lines.extend(_render_correction(correction))
    return lines


def _render_vendor_history(history: list[VendorHistoryEntry]) -> list[str]:
    lines = ["## VENDOR HISTORY (how earlier transactions for this vendor were booked)"]
    if not history:
        lines.append("- no prior booked transactions for this vendor")
        return lines
    for entry in history:
        lines.append(
            f"- {entry.transaction_id} {entry.booked_on.isoformat()} {entry.counterparty} "
            f"{_eur(entry.amount)} -> account {entry.account}"
        )
    return lines

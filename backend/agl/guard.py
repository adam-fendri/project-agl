from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from agl.grounding import (
    counterparty_agrees,
    party_of,
    referenced_documents,
    transactions_share_vendor,
)
from agl.models import (
    AnomalyType,
    Bill,
    Correction,
    GuardVerdict,
    Invoice,
    Outcome,
    Proposal,
    Rubriek,
    Transaction,
)
from agl.reconcile import validate_match
from agl.repository import Repository


def run_guard(
    proposal: Proposal,
    txn: Transaction,
    repo: Repository,
    settled_by: dict[str, list[str]],
) -> GuardVerdict:
    """Check the agent's proposal against hard facts before any auto-post.

    Verifies the account exists, the matched amount sums exactly (else partial), the matched
    document is not contradicted by a same-amount sibling whose counterparty disagrees (else
    ambiguous), settling an issued invoice is not re-booked as revenue (else double-counted),
    the document is not claimed by an earlier transaction (else duplicate), the direction is
    right, no prior correction is contradicted, no material missing document is unflagged, and
    no earlier transaction looks like the same payment (else a possible duplicate to review).
    Any failure DOWNGRADES to review via ``forced_outcome`` — it never rewrites the agent's choice.
    """
    accounts = repo.accounts(txn.customer_id)
    account_numbers = {a.number for a in accounts}
    rubriek_by_number = {a.number: a.rubriek for a in accounts}

    failures: list[str] = []

    if proposal.account not in account_numbers:
        failures.append("account_not_in_chart")

    if _correction_conflict(proposal, repo.corrections(txn.customer_id), rubriek_by_number):
        failures.append("correction_conflict")

    if proposal.match:
        invoices_by_id = {i.id: i for i in repo.invoices(txn.customer_id)}
        bills_by_id = {b.id: b for b in repo.bills(txn.customer_id)}
        referenced = set(referenced_documents(txn, set(invoices_by_id) | set(bills_by_id)))
        verdict = validate_match(txn, proposal.match, invoices_by_id, bills_by_id)
        if not verdict.direction_ok:
            failures.append("direction_mismatch")
        if not verdict.sums_exactly:
            failures.append("amount_mismatch")
        if referenced and not (referenced & set(proposal.match)):
            failures.append("reference_mismatch")
        if _amount_ambiguous(proposal.match, txn, invoices_by_id, bills_by_id, referenced):
            failures.append("amount_ambiguous")
        if _revenue_on_settlement(txn, proposal, rubriek_by_number):
            failures.append("revenue_on_settled_invoice")

        for doc in proposal.match:
            if _claimed_earlier(doc, txn, settled_by, repo):
                failures.append(f"duplicate:{doc}")

    anomaly = proposal.anomaly
    if anomaly is not None and anomaly.type is AnomalyType.MISSING_COUNTERPART:
        failures.append("missing_document")

    sibling = _fingerprint_duplicate(txn, repo)
    if sibling is not None:
        failures.append(f"possible_duplicate_payment:{sibling}")

    if not failures:
        return GuardVerdict(passed=True)

    return GuardVerdict(
        passed=False,
        failed_checks=failures,
        forced_outcome=_forced_outcome(failures),
    )


_DUPLICATE_WINDOW = timedelta(days=14)


def _forced_outcome(failures: list[str]) -> Outcome:
    if any(f.startswith("duplicate:") for f in failures):
        return Outcome.ANOMALY
    if "missing_document" in failures:
        return Outcome.REQUEST_DOCUMENT
    return Outcome.REVIEW


def _fingerprint_duplicate(txn: Transaction, repo: Repository) -> str | None:
    """An earlier transaction that looks like the same payment with no shared document.

    Same amount and same vendor within a tight window (well under the monthly cadence of recurring
    bills) flags a possible double payment the document-id collision map cannot see. Two distinct
    provided matches mean two distinct settlements, so they are not a duplicate.
    """
    this_provided = repo.provided_match(txn.id)
    for other in repo.transactions(txn.customer_id):
        if other.id == txn.id or (other.booked_on, other.id) >= (txn.booked_on, txn.id):
            continue
        if (
            abs(other.amount) != abs(txn.amount)
            or txn.booked_on - other.booked_on > _DUPLICATE_WINDOW
        ):
            continue
        other_provided = repo.provided_match(other.id)
        if (
            this_provided is not None
            and other_provided is not None
            and this_provided.document_id != other_provided.document_id
        ):
            continue
        if transactions_share_vendor(txn, other):
            return other.id
    return None


def _revenue_on_settlement(
    txn: Transaction,
    proposal: Proposal,
    rubriek_by_number: dict[str, Rubriek],
) -> bool:
    if txn.amount <= 0 or not any(did.startswith("INV-") for did in proposal.match):
        return False
    return rubriek_by_number.get(proposal.account) is Rubriek.REVENUE


def _resolve_document(
    doc_id: str,
    invoices_by_id: dict[str, Invoice],
    bills_by_id: dict[str, Bill],
) -> Invoice | Bill | None:
    if doc_id.startswith("INV-"):
        return invoices_by_id.get(doc_id)
    return bills_by_id.get(doc_id)


def _amount_ambiguous(
    match: list[str],
    txn: Transaction,
    invoices_by_id: dict[str, Invoice],
    bills_by_id: dict[str, Bill],
    referenced: set[str],
) -> bool:
    if referenced & set(match):
        return False
    matched = [
        doc
        for did in match
        if (doc := _resolve_document(did, invoices_by_id, bills_by_id)) is not None
    ]
    if not matched:
        return False
    total = sum((doc.gross for doc in matched), Decimal("0"))
    pool: list[Invoice | Bill] = (
        list(invoices_by_id.values()) if txn.amount > 0 else list(bills_by_id.values())
    )
    matched_ids = set(match)
    twin_exists = any(doc.gross == total and doc.id not in matched_ids for doc in pool)
    if not twin_exists:
        return False
    return not all(counterparty_agrees(party_of(doc), txn) for doc in matched)


def _claimed_earlier(
    doc: str,
    txn: Transaction,
    settled_by: dict[str, list[str]],
    repo: Repository,
) -> bool:
    """True when another transaction with an earlier (booked_on, id) also settled ``doc``.

    A duplicate is a cross-transaction fact: a document settled by two or more transactions. The later
    claimant (by booked_on, then id) is the duplicate; the earliest claimant is never flagged. Order of
    processing is irrelevant — the full ``settled_by`` map and each claimant's booked_on decide it.
    """
    this_key: tuple[date, str] = (txn.booked_on, txn.id)
    for other in settled_by.get(doc, []):
        if other == txn.id:
            continue
        other_txn = repo.transaction(other)
        other_key: tuple[date, str] = (
            (other_txn.booked_on, other) if other_txn is not None else (txn.booked_on, other)
        )
        if other_key < this_key:
            return True
    return False


def _correction_conflict(
    proposal: Proposal,
    corrections: list[Correction],
    rubriek_by_number: dict[str, Rubriek],
) -> bool:
    """A conflict only when the proposal contradicts the MOST RECENT correction for the vendor.

    A re-correction supersedes its predecessor, so the guard resolves the latest matching cost
    correction and never flags a decision against an account the accountant has already overruled.
    """
    effective: Correction | None = None
    for c in corrections:
        account = c.corrected_account
        if not c.vendor or account is None:
            continue
        if rubriek_by_number.get(account) is not Rubriek.COSTS:
            continue
        if not _vendor_matches(c.vendor, proposal.vendor):
            continue
        if effective is None or c.created_at > effective.created_at:
            effective = c
    return effective is not None and proposal.account != effective.corrected_account


def _vendor_matches(correction_vendor: str, proposal_vendor: str) -> bool:
    cv = correction_vendor.strip().casefold()
    pv = proposal_vendor.strip().casefold()
    if not cv or not pv:
        return False
    return cv in pv or pv in cv

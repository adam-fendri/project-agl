from __future__ import annotations

import re
from datetime import datetime

from agl.models import Account, Correction, Decision, Outcome, Rubriek, Transaction
from agl.repository import Repository

_BOILERPLATE = frozenset(
    {
        "sepa",
        "dd",
        "ovb",
        "overboeking",
        "incasso",
        "incassant",
        "mandaat",
        "kenmerk",
        "eref",
        "remi",
        "iban",
        "bic",
        "name",
        "trtp",
        "cred",
        "bea",
        "betaalpas",
        "pas",
        "nr",
        "mnd",
        "ref",
        "bv",
        "inc",
        "ltd",
        "nv",
    }
)


def canonical_vendor(txn: Transaction) -> str:
    """The vendor key the learning loop generalizes on: a clean merchant name, never the raw IBAN.

    A counterparty that reads as a name is kept as-is; an IBAN-shaped counterparty is discarded and the
    merchant is recovered from the leading name run of the description. The same key feeds correction
    selection and the guard, so a correction taught on one transaction lands on its siblings.
    """
    counterparty = txn.counterparty.strip()
    if counterparty and not _is_ibanish(counterparty) and any(c.isalpha() for c in counterparty):
        return counterparty
    return _vendor_from_description(txn.description) or counterparty


def vendor_cost_account(
    canonical: str,
    corrections: list[Correction],
    accounts: list[Account],
) -> str | None:
    """The cost account a prior correction pins for this vendor, or None.

    Scoped to expense (rubriek 4) corrections — the class the guard also backstops. Owner-draw and
    asset conventions hinge on the transaction's nature, judgement a deterministic agent withholds and
    defers to review.
    """
    target = _distinctive(canonical)
    if not target:
        return None
    rubriek_by_number = {account.number: account.rubriek for account in accounts}
    for correction in corrections:
        account = correction.corrected_account
        if not correction.vendor.strip() or account is None:
            continue
        if rubriek_by_number.get(account) is not Rubriek.COSTS:
            continue
        if _distinctive(correction.vendor) == target:
            return account
    return None


def apply_correction(
    repo: Repository,
    txn_id: str,
    corrected_account: str | None,
    corrected_match: list[str] | None,
    vendor: str | None = None,
) -> Correction:
    """Persist a correction to the runtime store, keyed on the vendor the agent identified.

    ``vendor`` is ``Decision.vendor`` (the agent's canonical vendor); the loop generalizes on it, so the
    caller passes it. It falls back to the transaction's canonical vendor, never the raw counterparty.
    Identical conventions already on record are returned unchanged rather than duplicated.
    """
    txn = repo.transaction(txn_id)
    if txn is None:
        raise KeyError(f"transaction {txn_id} not found")
    vendor_key = vendor if vendor and vendor.strip() else canonical_vendor(txn)
    match_rule = "+".join(corrected_match) if corrected_match else None

    for stored in repo.corrections(txn.customer_id):
        if (
            stored.vendor == vendor_key
            and stored.corrected_account == corrected_account
            and stored.corrected_match == match_rule
        ):
            return stored

    correction = Correction(
        id=f"L{len(repo.store.load()) + 1}",
        customer_id=txn.customer_id,
        transaction_id=txn.id,
        vendor=vendor_key,
        corrected_account=corrected_account,
        corrected_match=match_rule,
        note="",
        created_at=datetime.now(),
    )
    repo.store.append(correction)
    return correction


def pending_reruns(correction: Correction, decisions: list[Decision]) -> list[str]:
    """The pending (not yet auto-posted) decisions a new correction should move: the same-vendor siblings."""
    general = not correction.vendor.strip()
    vendor_tokens = _distinctive(correction.vendor)
    reruns: list[str] = []
    for decision in decisions:
        if decision.outcome is Outcome.AUTO_POST:
            continue
        if decision.transaction_id == correction.transaction_id:
            continue
        if general or (vendor_tokens & _distinctive(decision.vendor)):
            reruns.append(decision.transaction_id)
    return reruns


def _is_ibanish(token: str) -> bool:
    return (
        " " not in token
        and len(token) >= 12
        and any(c.isdigit() for c in token)
        and any(c.isalpha() for c in token)
    )


def _vendor_from_description(description: str) -> str:
    run: list[str] = []
    started = False
    for word in (w.strip(".,:*/") for w in description.split()):
        if _is_name_word(word):
            started = True
            run.append(word)
            if len(run) >= 2:
                break
        elif started:
            break
    return " ".join(run).title()


def _is_name_word(word: str) -> bool:
    return len(word) >= 2 and word.isalpha() and word.lower() not in _BOILERPLATE


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _distinctive(text: str) -> set[str]:
    return {token for token in _tokens(text) if len(token) >= 4}

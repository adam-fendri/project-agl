from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from agl.models import Bill, Invoice, Transaction


class Candidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_ids: list[str]
    party: str
    gross: Decimal
    relation: str
    gap: Decimal
    is_combination: bool


class MatchVerdict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document_ids: list[str]
    sums_exactly: bool
    gap: Decimal
    direction_ok: bool


def _tolerance(amount: Decimal) -> Decimal:
    return max(amount * Decimal("0.02"), Decimal("10"))


def _relation(gap: Decimal) -> str:
    if gap == 0:
        return "exact"
    return "short" if gap < 0 else "over"


def find_candidates(
    txn: Transaction,
    invoices: list[Invoice],
    bills: list[Bill],
) -> list[Candidate]:
    amount = abs(txn.amount)
    inflow = txn.amount > 0
    tol = _tolerance(amount)

    if inflow:
        docs = [(i.id, i.client, i.gross) for i in invoices]
    else:
        docs = [(b.id, b.supplier, b.gross) for b in bills]

    candidates: list[Candidate] = []
    for did, party, gross in docs:
        gap = amount - gross
        if abs(gap) <= tol:
            candidates.append(
                Candidate(
                    document_ids=[did],
                    party=party,
                    gross=gross,
                    relation=_relation(gap),
                    gap=gap,
                    is_combination=False,
                )
            )

    by_gross: dict[Decimal, list[tuple[str, str, Decimal]]] = {}
    for entry in docs:
        by_gross.setdefault(entry[2], []).append(entry)
    seen: set[tuple[str, str]] = set()
    for did, party, gross in docs:
        complement = amount - gross
        if complement <= 0:
            continue
        for did2, party2, _ in by_gross.get(complement, []):
            if did2 == did:
                continue
            ordered = sorted((did, did2))
            key = (ordered[0], ordered[1])
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                Candidate(
                    document_ids=[key[0], key[1]],
                    party=party if party == party2 else f"{party} + {party2}",
                    gross=amount,
                    relation="exact",
                    gap=Decimal("0"),
                    is_combination=True,
                )
            )
    return candidates


def validate_match(
    txn: Transaction,
    document_ids: list[str],
    invoices_by_id: dict[str, Invoice],
    bills_by_id: dict[str, Bill],
) -> MatchVerdict:
    amount = abs(txn.amount)
    inflow = txn.amount > 0
    direction_ok = bool(document_ids)
    gross_sum = Decimal("0")
    for did in document_ids:
        if did.startswith("INV-"):
            inv = invoices_by_id.get(did)
            if inv is None or not inflow:
                direction_ok = False
                continue
            gross_sum += inv.gross
        else:
            bill = bills_by_id.get(did)
            if bill is None or inflow:
                direction_ok = False
                continue
            gross_sum += bill.gross
    gap = amount - gross_sum
    return MatchVerdict(
        document_ids=document_ids,
        sums_exactly=(gap == 0 and bool(document_ids)),
        gap=gap,
        direction_ok=direction_ok,
    )

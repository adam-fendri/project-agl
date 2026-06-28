from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel

from agl.models import (
    Account,
    Bill,
    Correction,
    DocumentStatus,
    GroundTruth,
    Invoice,
    Outcome,
    ProvidedMatch,
    Transaction,
    TransactionType,
)

SOURCE = Path("/Users/adamvox/projects/neno-challenge/data")
OUT = Path("/Users/adamvox/projects/neno-challenge/backend/seeds")
CUSTOMER = "studio-vondel"

DECISION = {
    "AUTO": Outcome.AUTO_POST,
    "REVIEW": Outcome.REVIEW,
    "ANOMALY": Outcome.ANOMALY,
    "REQUEST": Outcome.REQUEST_DOCUMENT,
}

PROVIDED_OVERRIDE = {
    "T046": "B-11",
    "T072": "INV-2026-005",
    "T074": "INV-2026-004",
    "T076": "INV-2026-006",
}


def cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table_rows(text: str, first_cell: re.Pattern[str]) -> list[list[str]]:
    out: list[list[str]] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        row = cells(line)
        if row and first_cell.fullmatch(row[0]):
            out.append(row)
    return out


def dutch_amount(s: str) -> Decimal:
    s = s.strip().replace("+", "").replace(".", "").replace(",", ".")
    return Decimal(s)


def us_amount(s: str) -> Decimal:
    s = re.sub(r"\(.*?\)", "", s).replace("*", "").replace(",", "").strip()
    return Decimal(s)


def account_number(cell: str) -> str:
    return re.sub(r"[^0-9]", "", cell.split()[0])


def doc_status(cell: str) -> DocumentStatus:
    return DocumentStatus.UNPAID if "UNPAID" in cell.upper() else DocumentStatus.PAID


def txn_type(description: str) -> TransactionType:
    d = description.lower()
    if "overboeking" in d:
        return TransactionType.SEPA_TRANSFER
    if "incasso" in d:
        return TransactionType.SEPA_DIRECT_DEBIT
    if "ideal" in d:
        return TransactionType.IDEAL
    if "bea" in d or "betaalpas" in d:
        return TransactionType.CARD
    return TransactionType.OTHER


def _digest(seed: str) -> str:
    return hashlib.md5(seed.encode()).hexdigest().upper()


def _fake_iban(seed: str) -> str:
    d = _digest(seed)
    return f"NL{d[0:2]}INGB{d[2:12]}"


def _trim_edges(s: str) -> str:
    return re.sub(r"^[\s.,&-]+|[\s.,&-]+$", "", s)


def _abbrev(name: str, width: int = 20) -> str:
    n = re.sub(
        r"\b(B\.?V\.?|N\.?V\.?|Inc\.?|Ltd\.?|LLC|EMEA|Ireland|Technologies|Systems|Groep|Zakelijk)\b",
        "",
        name,
        flags=re.IGNORECASE,
    )
    n = _trim_edges(re.sub(r"\s+", " ", n).strip().upper())
    return _trim_edges((n or name.upper().strip())[:width])


def _remittance(description: str) -> str:
    s = re.sub(r"^\s*(sepa\s+)?(overboeking|incasso)\s+", "", description, flags=re.IGNORECASE)
    s = re.sub(r"^\s*bea\s+betaalpas\s+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^\s*ideal\s+", "", s, flags=re.IGNORECASE)
    s = s.strip().upper()
    return "" if "GEEN OMSCHRIJVING" in s else s


def harden(tid: str, counterparty: str, description: str, ttype: TransactionType) -> tuple[str, str]:
    d = _digest(tid)
    name = counterparty.upper()
    remi = _remittance(description)
    eref = d[:8]
    mandate = d[8:13]
    incassant = f"NL{d[13:15]}ZZZ{d[15:24]}0000"
    iban = _fake_iban(tid)
    pas = int(d[24:26], 16) % 900 + 100
    variant = int(d[2:4], 16) % 3

    if ttype == TransactionType.SEPA_TRANSFER:
        if variant == 0:
            body = f"/TRTP/SEPA OVERBOEKING/IBAN/{iban}/BIC/INGBNL2A/NAME/{name}/REMI/{remi}/EREF/{eref}"
            return _abbrev(counterparty), body.replace("/REMI//EREF", "/EREF")
        if variant == 1:
            return iban, f"SEPA OVB {name} {remi} KENMERK {eref}".replace("  ", " ").strip()
        return _abbrev(counterparty), f"OVERBOEKING {name} {remi} REF {eref}".replace("  ", " ").strip()
    if ttype == TransactionType.SEPA_DIRECT_DEBIT:
        if variant == 0:
            return _abbrev(counterparty), (
                f"SEPA INCASSO {name} MANDAAT {mandate} INCASSANT {incassant} {remi}".strip()
            )
        if variant == 1:
            return _abbrev(counterparty), f"INCASSO {remi} MND {mandate} CRED {name}".replace("  ", " ").strip()
        return iban, f"SEPA DD {name} {remi} INCASSANT {incassant}".replace("  ", " ").strip()
    if ttype == TransactionType.IDEAL:
        return _abbrev(counterparty), f"IDEAL {name} {remi} KENMERK {eref}".replace("  ", " ").strip()
    if ttype == TransactionType.CARD:
        return _abbrev(counterparty), f"BEA, BETAALPAS PAS{pas:03d} NR:{eref[:5]} {name} {remi}".replace("  ", " ").strip()
    return name, (remi or f"REF {eref}")


def parse_accounts() -> list[Account]:
    text = (SOURCE / "chart_of_accounts.md").read_text()
    out: list[Account] = []
    for row in table_rows(text, re.compile(r"\d{4}")):
        nr = row[0]
        out.append(
            Account(
                number=nr,
                customer_id=CUSTOMER,
                name_nl=row[1],
                name_en=row[2],
                rubriek=nr[0],  # type: ignore[arg-type] - validated by the enum
                rgs_group=row[3].strip("`").replace("~", "").strip(),
            )
        )
    return out


def parse_documents() -> tuple[list[Invoice], list[Bill]]:
    text = (SOURCE / "cast_and_documents.md").read_text()
    invoices = [
        Invoice(
            id=row[0],
            customer_id=CUSTOMER,
            client=row[1],
            issued_on=date.fromisoformat(row[2]),
            net=us_amount(row[3]),
            vat=us_amount(row[4]),
            gross=us_amount(row[5]),
            status=doc_status(row[6]),
        )
        for row in table_rows(text, re.compile(r"INV-\d{4}-\d{3}"))
    ]
    bills = [
        Bill(
            id=row[0],
            customer_id=CUSTOMER,
            supplier=row[1],
            received_on=date.fromisoformat(row[2]),
            net=us_amount(row[3]),
            vat=us_amount(row[4]),
            gross=us_amount(row[5]),
            account=account_number(row[6]),
            status=doc_status(row[7]),
        )
        for row in table_rows(text, re.compile(r"B-\d{2}"))
    ]
    return invoices, bills


def parse_transactions() -> tuple[list[Transaction], list[GroundTruth]]:
    text = (SOURCE / "transactions.md").read_text()
    transactions: list[Transaction] = []
    truth: list[GroundTruth] = []
    for row in table_rows(text, re.compile(r"T\d{3}")):
        tid, mmdd, amount, counterparty, omschrijving, gt_acct, match, decision = row[:8]
        month, day = (int(x) for x in mmdd.split("-"))
        ttype = txn_type(omschrijving)
        messy_cp, messy_desc = harden(tid, counterparty, omschrijving, ttype)
        transactions.append(
            Transaction(
                id=tid,
                customer_id=CUSTOMER,
                booked_on=date(2026, month, day),
                amount=dutch_amount(amount),
                counterparty=messy_cp,
                description=messy_desc,
                type=ttype,
            )
        )
        match_docs: list[str] = []
        cleaned = match.replace("?", "").strip()
        if cleaned and cleaned != "-":
            match_docs = [m.strip() for m in cleaned.split("+")]
            match_docs = [m if m.startswith(("B-", "INV-")) else f"INV-2026-{m}" for m in match_docs]
        truth.append(
            GroundTruth(
                transaction_id=tid,
                account=account_number(gt_acct),
                match=match_docs if decision != "ANOMALY" else [],
                outcome=DECISION[decision],
            )
        )
    return transactions, truth


def build_provided_matches(truth: list[GroundTruth]) -> list[ProvidedMatch]:
    out: list[ProvidedMatch] = []
    for gt in truth:
        if gt.transaction_id in PROVIDED_OVERRIDE:
            doc = PROVIDED_OVERRIDE[gt.transaction_id]
        elif gt.match:
            doc = gt.match[0]
        else:
            continue
        out.append(ProvidedMatch(transaction_id=gt.transaction_id, document_id=doc))
    return out


def settling_docs(provided: list[ProvidedMatch]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for pm in provided:
        out.setdefault(pm.transaction_id, set()).add(pm.document_id)
    return out


def match_failures(truth: list[GroundTruth], provided: list[ProvidedMatch]) -> tuple[set[str], int]:
    infra = settling_docs(provided)
    wrong: set[str] = set()
    correct_positive = 0
    for gt in truth:
        proposed = infra.get(gt.transaction_id, set())
        if proposed == set(gt.match):
            if proposed:
                correct_positive += 1
        else:
            wrong.add(gt.transaction_id)
    return wrong, correct_positive


def build_corrections() -> list[Correction]:
    ts = datetime(2025, 12, 15, 9, 0, 0)
    return [
        Correction(
            id="C1",
            customer_id=CUSTOMER,
            vendor="J. de Vries",
            corrected_account="4100",
            note="Personal-name SEPA transfer, not one of the payrolled employees, with a freelance "
            "invoice ref -> freelancer 4100, not wages 4000.",
            created_at=ts,
        ),
        Correction(
            id="C2",
            customer_id=CUSTOMER,
            vendor="Google Ads",
            corrected_account="4400",
            note="GOOGLE *ADS -> marketing 4400; GOOGLE *GSUITE / Workspace -> software 4300. Same "
            "vendor root, split by product.",
            created_at=ts,
        ),
        Correction(
            id="C3",
            customer_id=CUSTOMER,
            vendor="",
            corrected_account="0150",
            note="Hardware with net value >= ~EUR450 is an asset (0150, depreciated); below that, "
            "office supplies (4500).",
            created_at=ts,
        ),
        Correction(
            id="C4",
            customer_id=CUSTOMER,
            vendor="T. Bakker",
            corrected_account="0600",
            note="A transfer to the owner that is NOT the fixed monthly salary (off-cycle date, round "
            "amount, no description) is an owner draw 0600, never an expense.",
            created_at=ts,
        ),
        Correction(
            id="C5",
            customer_id=CUSTOMER,
            vendor="",
            corrected_match="by_counterparty",
            note="When more than one open invoice shares the same amount, disambiguate by the paying "
            "counterparty, not amount alone.",
            created_at=ts,
        ),
    ]


def dump(name: str, records: Sequence[BaseModel]) -> None:
    payload = [r.model_dump(mode="json") for r in records]
    (OUT / f"{name}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def verify(
    accounts: list[Account],
    invoices: list[Invoice],
    bills: list[Bill],
    transactions: list[Transaction],
    truth: list[GroundTruth],
    provided: list[ProvidedMatch],
) -> None:
    assert len(accounts) >= 33, f"expected >=33 accounts, got {len(accounts)}"
    assert len(transactions) == 100, f"expected 100 transactions, got {len(transactions)}"
    assert len(invoices) == 10, f"expected 10 invoices, got {len(invoices)}"
    assert len(bills) == 20, f"expected 20 bills, got {len(bills)}"
    assert len(provided) == 26, f"expected 26 provided matches, got {len(provided)}"

    for inv in invoices:
        assert inv.net + inv.vat == inv.gross, f"{inv.id}: {inv.net}+{inv.vat}!={inv.gross}"
    for b in bills:
        assert b.net + b.vat == b.gross, f"{b.id}: {b.net}+{b.vat}!={b.gross}"

    by_outcome = {o: 0 for o in Outcome}
    for gt in truth:
        by_outcome[gt.outcome] += 1
    assert by_outcome[Outcome.AUTO_POST] == 81, by_outcome
    assert by_outcome[Outcome.REVIEW] == 16, by_outcome
    assert by_outcome[Outcome.ANOMALY] == 1, by_outcome
    assert by_outcome[Outcome.REQUEST_DOCUMENT] == 2, by_outcome

    by_id = {t.id: t for t in transactions}
    receivables = [gt for gt in truth if gt.account == "1300"]
    assert len(receivables) == 7, f"expected 7 invoice-settling inflows on 1300, got {len(receivables)}"
    assert all(gt.account != "8000" for gt in truth), "no bank line books to 8000 under accrual"
    for gt in receivables:
        assert by_id[gt.transaction_id].amount > 0, f"{gt.transaction_id}: 1300 receivable must be an inflow"
        assert gt.match and all(d.startswith("INV-") for d in gt.match), f"{gt.transaction_id}: 1300 settles an invoice"

    wrong, correct_positive = match_failures(truth, provided)
    assert wrong == {"T046", "T072", "T074", "T076"}, f"unexpected planted failures: {wrong}"
    assert correct_positive == 22, f"expected 22 correct positive matches, got {correct_positive}"

    paid = sum(1 for b in bills if b.status is DocumentStatus.PAID)
    assert paid == 18 and len(bills) - paid == 2, f"expected 18 paid / 2 open bills, got {paid}/{len(bills) - paid}"

    doc_ids = {i.id for i in invoices} | {b.id for b in bills}
    for pm in provided:
        assert pm.document_id in doc_ids, f"provided match to unknown doc {pm.document_id}"
    for gt in truth:
        for d in gt.match:
            assert d in doc_ids, f"{gt.transaction_id}: GT match to unknown doc {d}"

    t001 = next(t for t in transactions if t.id == "T001")
    assert t001.amount == Decimal("-4235.00"), t001.amount
    inv002 = next(i for i in invoices if i.id == "INV-2026-002")
    assert inv002.gross == Decimal("5082"), inv002.gross
    t076 = next(gt for gt in truth if gt.transaction_id == "T076")
    assert t076.match == ["INV-2026-006", "INV-2026-007"], t076.match


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    accounts = parse_accounts()
    invoices, bills = parse_documents()
    transactions, truth = parse_transactions()
    provided = build_provided_matches(truth)
    corrections = build_corrections()

    verify(accounts, invoices, bills, transactions, truth, provided)

    by_id = {t.id: t for t in transactions}
    samples = ["T001", "T031", "T066", "T005", "T068", "T016", "T019", "T043", "T042", "T040", "T046", "T096"]
    print("--- hardening samples (messy seed; compare to the clean source table) ---")
    for tid in samples:
        t = by_id[tid]
        print(f"  {tid} [{t.type.value}] cp={t.counterparty!r} | {t.description}")
    print("---")

    assert len(corrections) == 5, f"expected 5 corrections, got {len(corrections)}"
    by_outcome = {o: 0 for o in Outcome}
    for gt in truth:
        by_outcome[gt.outcome] += 1
    wrong, correct_positive = match_failures(truth, provided)
    accuracy = (len(truth) - len(wrong)) / len(truth)
    precision = correct_positive / len(provided)
    paid = sum(1 for b in bills if b.status is DocumentStatus.PAID)
    print("--- distributions ---")
    print(
        f"  counts: {len(transactions)} txns, {len(invoices)} invoices, {len(bills)} bills, "
        f"{len(corrections)} corrections, {len(provided)} provided matches"
    )
    print(
        f"  outcomes: auto_post={by_outcome[Outcome.AUTO_POST]} review={by_outcome[Outcome.REVIEW]} "
        f"anomaly={by_outcome[Outcome.ANOMALY]} request_document={by_outcome[Outcome.REQUEST_DOCUMENT]}"
    )
    print(
        f"  inflow accounting: 1300 Debiteuren={sum(1 for gt in truth if gt.account == '1300')} "
        f"8000 Omzet={sum(1 for gt in truth if gt.account == '8000')} (revenue is recognized off the bank feed, at invoicing)"
    )
    print(
        f"  provided matches: {len(provided)} positive ({correct_positive} correct, {len(wrong)} wrong {sorted(wrong)})"
    )
    print(
        f"  match-decision accuracy across {len(truth)} txns = {accuracy:.2f}; "
        f"positive-match precision = {correct_positive}/{len(provided)} = {precision:.2f}"
    )
    print(f"  bills: {paid} paid, {len(bills) - paid} unpaid (open AP)")
    print("---")

    dump("accounts", accounts)
    dump("invoices", invoices)
    dump("bills", bills)
    dump("transactions", transactions)
    dump("ground_truth", truth)
    dump("provided_matches", provided)
    dump("corrections", corrections)

    print(
        f"OK: {len(accounts)} accounts, {len(invoices)} invoices, {len(bills)} bills, "
        f"{len(transactions)} transactions, {len(provided)} provided matches, "
        f"{len(corrections)} corrections -> {OUT}"
    )


if __name__ == "__main__":
    main()

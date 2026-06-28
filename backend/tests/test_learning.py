from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from agl.grounding import build_evidence
from agl.learning import apply_correction, canonical_vendor, pending_reruns, vendor_cost_account
from agl.models import (
    Account,
    Confidence,
    Correction,
    Decision,
    MatchStatus,
    Outcome,
    Rubriek,
    Transaction,
    TransactionType,
)
from agl.repository import SEEDS, Repository

CUSTOMER = "studio-vondel"


def _runtime_repo(tmp_path: Path) -> Repository:
    return Repository(runtime_dir=tmp_path)


def _software_account() -> Account:
    return Account(
        number="4300",
        customer_id=CUSTOMER,
        name_nl="Software",
        name_en="Software",
        rubriek=Rubriek.COSTS,
        rgs_group="WBedAandKnt",
    )


def _figma_txn() -> Transaction:
    return Transaction(
        id="t-figma",
        customer_id=CUSTOMER,
        booked_on=date(2026, 1, 6),
        amount=Decimal("-217.80"),
        counterparty="NLF3INGB2CC68014EF",
        description="SEPA DD FIGMA INC FIGMA *PRO SEAT INCASSANT NLD1ZZZ51D7A7FD30000",
        type=TransactionType.SEPA_DIRECT_DEBIT,
    )


def _correction(vendor: str, account: str) -> Correction:
    return Correction(
        id="L0",
        customer_id=CUSTOMER,
        transaction_id="t-figma",
        vendor=vendor,
        corrected_account=account,
        corrected_match=None,
        note="",
        created_at=datetime(2026, 1, 1),
    )


def _correction_at(vendor: str, account: str, created_at: datetime) -> Correction:
    return _correction(vendor, account).model_copy(update={"created_at": created_at})


def _costs_account(number: str) -> Account:
    return _software_account().model_copy(update={"number": number})


def _decision(transaction_id: str, vendor: str, account: str) -> Decision:
    return Decision(
        transaction_id=transaction_id,
        vendor=vendor,
        account=account,
        account_reasoning="r",
        account_confidence=Confidence.MEDIUM,
        match=[],
        match_reasoning=None,
        match_status=MatchStatus.NONE,
        match_confidence=Confidence.LOW,
        anomaly=None,
        confidence_signals=[],
        outcome=Outcome.REVIEW,
        sources=[],
    )


def test_canonical_vendor_recovers_name_from_iban_counterparty() -> None:
    assert canonical_vendor(_figma_txn()) == "Figma"


def test_canonical_vendor_keeps_a_clean_counterparty() -> None:
    txn = _figma_txn().model_copy(update={"counterparty": "ACME BV"})
    assert canonical_vendor(txn) == "ACME BV"


def test_vendor_cost_account_returns_none_without_a_correction() -> None:
    assert vendor_cost_account("Figma", [], [_software_account()]) is None


def test_vendor_cost_account_selects_the_corrected_cost_account() -> None:
    account = vendor_cost_account("Figma", [_correction("Figma", "4300")], [_software_account()])
    assert account == "4300"


def test_vendor_cost_account_prefers_the_most_recent_correction() -> None:
    accounts = [_costs_account("4300"), _costs_account("4500")]
    older = _correction_at("Figma", "4300", datetime(2026, 1, 1))
    newer = _correction_at("Figma", "4500", datetime(2026, 2, 1))

    assert vendor_cost_account("Figma", [older, newer], accounts) == "4500"
    assert vendor_cost_account("Figma", [newer, older], accounts) == "4500"


def test_apply_correction_writes_runtime_store_not_seed(tmp_path: Path) -> None:
    seed_before = json.loads((SEEDS / "corrections.json").read_text())
    repo = _runtime_repo(tmp_path)

    correction = apply_correction(repo, "T004", "4300", None, vendor="Figma")

    runtime = json.loads((tmp_path / "corrections.json").read_text())
    seed_after = json.loads((SEEDS / "corrections.json").read_text())
    assert correction.vendor == "Figma"
    assert len(runtime) == 1
    assert seed_after == seed_before
    assert len(seed_after) == 5
    assert any(c.id == correction.id for c in repo.reload().corrections(CUSTOMER))


def test_apply_correction_dedupes(tmp_path: Path) -> None:
    repo = _runtime_repo(tmp_path)

    first = apply_correction(repo, "T004", "4300", None, vendor="Figma")
    second = apply_correction(repo.reload(), "T099", "4300", None, vendor="Figma")

    assert first.id == second.id
    assert len(json.loads((tmp_path / "corrections.json").read_text())) == 1


def test_apply_correction_most_recent_account_wins(tmp_path: Path) -> None:
    repo = _runtime_repo(tmp_path)
    rubriek = {a.number: a.rubriek for a in repo.accounts(CUSTOMER)}
    assert rubriek.get("4300") is Rubriek.COSTS
    assert rubriek.get("4500") is Rubriek.COSTS

    apply_correction(repo, "T004", "4300", None, vendor="Figma")
    apply_correction(repo.reload(), "T004", "4500", None, vendor="Figma")

    reloaded = repo.reload()
    effective = vendor_cost_account(
        "Figma", reloaded.corrections(CUSTOMER), reloaded.accounts(CUSTOMER)
    )
    assert effective == "4500"
    assert len(reloaded.store.load()) == 2


def test_apply_correction_rejects_unknown_account(tmp_path: Path) -> None:
    repo = _runtime_repo(tmp_path)

    with pytest.raises(ValueError, match="unknown account"):
        apply_correction(repo, "T004", "9999", None, vendor="Figma")

    assert not (tmp_path / "corrections.json").exists()
    assert repo.store.load() == []


def test_apply_correction_rejects_unknown_document(tmp_path: Path) -> None:
    repo = _runtime_repo(tmp_path)

    with pytest.raises(ValueError, match="unknown document"):
        apply_correction(repo, "T004", None, ["INV-9999"], vendor="Figma")

    assert not (tmp_path / "corrections.json").exists()
    assert repo.store.load() == []


def test_apply_correction_accepts_real_account_and_document(tmp_path: Path) -> None:
    repo = _runtime_repo(tmp_path)

    correction = apply_correction(repo, "T004", "4300", ["INV-2026-001"], vendor="Figma")

    assert correction.corrected_account == "4300"
    assert correction.corrected_match == "INV-2026-001"
    assert len(repo.store.load()) == 1


def test_pending_reruns_targets_vendor_siblings_only() -> None:
    correction = _correction("Figma", "4300")
    cold = [
        _decision("T004", "Figma", "4000"),
        _decision("T099", "Figma", "4000"),
        _decision("T050", "Adobe", "4000"),
    ]

    reran = pending_reruns(correction, cold)

    assert "T099" in reran
    assert "T050" not in reran


def test_correction_enters_a_sibling_transactions_evidence(tmp_path: Path) -> None:
    repo = _runtime_repo(tmp_path)
    apply_correction(repo, "T004", "4300", None, vendor="Figma")
    repo = repo.reload()

    sibling = repo.transaction("T099")
    assert sibling is not None
    evidence = build_evidence(sibling, repo, CUSTOMER)

    assert any(c.corrected_account == "4300" for c in evidence.corrections)

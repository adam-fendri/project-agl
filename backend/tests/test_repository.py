from __future__ import annotations

import json
from pathlib import Path

import pytest

from agl.learning import apply_correction, pending_reruns
from agl.models import (
    Account,
    Confidence,
    Decision,
    MatchStatus,
    Outcome,
    Rubriek,
)
from agl.repository import SEEDS, Repository

CUSTOMER = "studio-vondel"


def _new_account(number: str = "4990") -> Account:
    return Account(
        number=number,
        customer_id=CUSTOMER,
        name_nl="Design tools",
        name_en="Design tools",
        rubriek=Rubriek.COSTS,
        rgs_group="",
    )


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


def test_add_account_persists_runtime_not_seed(tmp_path: Path) -> None:
    seed_before = json.loads((SEEDS / "accounts.json").read_text())
    repo = Repository(runtime_dir=tmp_path)

    grown = repo.add_account(_new_account())

    runtime = json.loads((tmp_path / "accounts.json").read_text())
    assert runtime == [_new_account().model_dump(mode="json")]
    assert json.loads((SEEDS / "accounts.json").read_text()) == seed_before
    assert "4990" in {a.number for a in grown.accounts(CUSTOMER)}
    assert "4990" in {a.number for a in repo.reload().accounts(CUSTOMER)}


def test_add_account_rejects_duplicate_number(tmp_path: Path) -> None:
    repo = Repository(runtime_dir=tmp_path)
    existing = repo.accounts(CUSTOMER)[0].number

    with pytest.raises(ValueError, match="already in the chart"):
        repo.add_account(_new_account(existing))

    assert not (tmp_path / "accounts.json").exists()


def test_correction_to_unknown_account_rejected_before_the_account_exists(tmp_path: Path) -> None:
    repo = Repository(runtime_dir=tmp_path)

    with pytest.raises(ValueError, match="unknown account"):
        apply_correction(repo, "T004", "4990", None, vendor="Figma")


def test_correction_to_new_account_succeeds_and_targets_siblings(tmp_path: Path) -> None:
    repo = Repository(runtime_dir=tmp_path).add_account(_new_account())

    correction = apply_correction(repo, "T004", "4990", None, vendor="Figma")

    assert correction.corrected_account == "4990"
    reran = pending_reruns(
        correction,
        [
            _decision("T004", "Figma", "4000"),
            _decision("T099", "Figma", "4000"),
            _decision("T050", "Adobe", "4000"),
        ],
    )
    assert "T099" in reran
    assert "T050" not in reran

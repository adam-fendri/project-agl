from __future__ import annotations

import pytest

from agl.guard import run_guard
from agl.models import Confidence, Outcome, Proposal, Transaction
from agl.repository import Repository

CUSTOMER = "studio-vondel"


@pytest.fixture(scope="module")
def repo() -> Repository:
    return Repository()


@pytest.fixture(scope="module")
def by_id(repo: Repository) -> dict[str, Transaction]:
    return {t.id: t for t in repo.transactions(CUSTOMER)}


def _proposal(vendor: str, account: str, match: list[str]) -> Proposal:
    return Proposal(
        vendor=vendor,
        account=account,
        account_reasoning="test",
        account_confidence=Confidence.HIGH,
        match=match,
        match_reasoning="test" if match else None,
        match_confidence=Confidence.HIGH,
    )


def test_resolved_claim_by_earlier_transaction_forces_anomaly(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    claimed_by = {"B-11": ["T040"]}
    proposal = _proposal("Studio Pixel", "4100", ["B-11"])

    verdict = run_guard(proposal, by_id["T046"], repo, claimed_by)

    assert "duplicate:B-11" in verdict.failed_checks
    assert verdict.forced_outcome is Outcome.ANOMALY


def test_repointed_swap_is_not_flagged_as_duplicate(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    claimed_by = {"INV-2026-004": ["T072"]}
    proposal = _proposal("Lumen Retail", "1300", ["INV-2026-005"])

    verdict = run_guard(proposal, by_id["T074"], repo, claimed_by)

    assert not any(check.startswith("duplicate:") for check in verdict.failed_checks)
    assert verdict.forced_outcome is not Outcome.ANOMALY

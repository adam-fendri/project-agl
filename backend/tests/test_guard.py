from __future__ import annotations

import pytest

from agl.guard import run_guard
from agl.models import Anomaly, AnomalyType, Confidence, Outcome, Proposal, Transaction
from agl.repository import Repository

CUSTOMER = "studio-vondel"


@pytest.fixture(scope="module")
def repo() -> Repository:
    return Repository()


@pytest.fixture(scope="module")
def by_id(repo: Repository) -> dict[str, Transaction]:
    return {t.id: t for t in repo.transactions(CUSTOMER)}


def _proposal(
    vendor: str,
    account: str,
    match: list[str],
    anomaly: Anomaly | None = None,
) -> Proposal:
    return Proposal(
        vendor=vendor,
        account=account,
        account_reasoning="test",
        account_confidence=Confidence.HIGH,
        match=match,
        match_reasoning="test" if match else None,
        match_confidence=Confidence.HIGH,
        anomaly=anomaly,
    )


def test_duplicate_later_transaction_forced_to_anomaly(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    claimed_by = {"B-11": ["T040", "T046"]}
    proposal = _proposal("Studio Pixel", "4100", ["B-11"])

    verdict = run_guard(proposal, by_id["T046"], repo, claimed_by)

    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.ANOMALY
    assert "duplicate:B-11" in verdict.failed_checks


def test_duplicate_first_claimant_passes(repo: Repository, by_id: dict[str, Transaction]) -> None:
    claimed_by = {"B-11": ["T040", "T046"]}
    proposal = _proposal("Studio Pixel", "4100", ["B-11"])

    verdict = run_guard(proposal, by_id["T040"], repo, claimed_by)

    assert verdict.passed is True
    assert verdict.forced_outcome is None


def test_short_pay_forced_to_review(repo: Repository, by_id: dict[str, Transaction]) -> None:
    claimed_by = {"INV-2026-002": ["T045"]}
    proposal = _proposal("Brightseed", "8000", ["INV-2026-002"])

    verdict = run_guard(proposal, by_id["T045"], repo, claimed_by)

    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.REVIEW
    assert "amount_mismatch" in verdict.failed_checks


def test_account_not_in_chart_forced_to_review(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Slack", "9999", [])

    verdict = run_guard(proposal, by_id["T006"], repo, {})

    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.REVIEW
    assert "account_not_in_chart" in verdict.failed_checks


def test_direction_mismatch_forced_to_review(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Studio Pixel", "4100", ["INV-2026-002"])

    verdict = run_guard(proposal, by_id["T046"], repo, {})

    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.REVIEW
    assert "direction_mismatch" in verdict.failed_checks


def test_conditional_owner_draw_correction_does_not_block_salary(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("T. Bakker", "4000", [])

    verdict = run_guard(proposal, by_id["T019"], repo, {})

    assert verdict.passed is True
    assert verdict.forced_outcome is None


def test_exact_vendor_correction_conflict_forced_to_review(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("J. de Vries", "4000", [])

    verdict = run_guard(proposal, by_id["T043"], repo, {})

    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.REVIEW
    assert "correction_conflict" in verdict.failed_checks


def test_documentless_recurring_payment_passes(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Slack", "4300", [])

    verdict = run_guard(proposal, by_id["T006"], repo, {})

    assert verdict.passed is True


def test_agent_flagged_missing_counterpart_forced_to_request_document(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal(
        "Stipt Service",
        "4900",
        [],
        anomaly=Anomaly(type=AnomalyType.MISSING_COUNTERPART, reason="invoice referenced, no bill"),
    )

    verdict = run_guard(proposal, by_id["T096"], repo, {})

    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.REQUEST_DOCUMENT
    assert "missing_document" in verdict.failed_checks


def test_clean_exact_match_passes(repo: Repository, by_id: dict[str, Transaction]) -> None:
    claimed_by = {"B-11": ["T040", "T046"]}
    proposal = _proposal("Studio Pixel", "4100", ["B-11"])

    verdict = run_guard(proposal, by_id["T040"], repo, claimed_by)

    assert verdict.passed is True


def test_same_amount_collision_without_corroboration_forced_to_review(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Lumen Retail", "1300", ["INV-2026-005"])

    verdict = run_guard(proposal, by_id["T072"], repo, {})

    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.REVIEW
    assert "amount_ambiguous" in verdict.failed_checks


def test_same_amount_collision_with_corroboration_passes(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Voss & Partners", "1300", ["INV-2026-004"])

    verdict = run_guard(proposal, by_id["T072"], repo, {})

    assert verdict.passed is True
    assert "amount_ambiguous" not in verdict.failed_checks


def test_settled_invoice_rebooked_as_revenue_forced_to_review(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Mendo", "8000", ["INV-2026-003"])

    verdict = run_guard(proposal, by_id["T039"], repo, {})

    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.REVIEW
    assert "revenue_on_settled_invoice" in verdict.failed_checks


def test_settled_invoice_booked_to_receivable_passes(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Mendo", "1300", ["INV-2026-003"])

    verdict = run_guard(proposal, by_id["T039"], repo, {})

    assert verdict.passed is True


def test_unmatched_rapid_duplicate_surfaced_for_review(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("Studio Pixel", "4100", [])

    verdict = run_guard(proposal, by_id["T046"], repo, {})

    assert verdict.passed is False
    assert verdict.forced_outcome is Outcome.REVIEW
    assert "possible_duplicate_payment:T040" in verdict.failed_checks


def test_monthly_recurring_payment_is_not_a_duplicate(
    repo: Repository, by_id: dict[str, Transaction]
) -> None:
    proposal = _proposal("KPN", "4510", [])

    verdict = run_guard(proposal, by_id["T070"], repo, {})

    assert verdict.passed is True

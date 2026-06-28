from __future__ import annotations

import json

from agl.eval import corrections_suppressed, lift_report, moved_rows, run_eval
from agl.models import Confidence, Decision, MatchStatus, Outcome
from agl.repository import SEEDS, Repository

CUSTOMER = "studio-vondel"


def _decision(
    transaction_id: str,
    account: str,
    match: list[str],
    outcome: Outcome,
) -> Decision:
    return Decision(
        transaction_id=transaction_id,
        vendor="V",
        account=account,
        account_reasoning="r",
        account_confidence=Confidence.HIGH,
        match=match,
        match_reasoning=None,
        match_status=MatchStatus.FULL if match else MatchStatus.NONE,
        match_confidence=Confidence.HIGH,
        anomaly=None,
        confidence_signals=[],
        outcome=outcome,
        sources=[],
    )


def test_gate_scores_each_outcome_precision_and_recall() -> None:
    repo = Repository()
    decisions = [
        _decision("T003", "4300", [], Outcome.AUTO_POST),
        _decision("T010", "4410", [], Outcome.REVIEW),
        _decision("T046", "4100", [], Outcome.ANOMALY),
        _decision("T049", "0150", [], Outcome.REQUEST_DOCUMENT),
    ]

    report = run_eval(decisions, repo)

    for name in ("auto_post", "review", "anomaly", "request_document"):
        gate = report.gates[name]
        assert gate.predicted == 1
        assert gate.expected == 1
        assert gate.correct == 1
        assert gate.precision == 1.0
        assert gate.recall == 1.0


def test_review_gate_penalizes_over_deferral() -> None:
    repo = Repository()
    decisions = [
        _decision("T003", "4300", [], Outcome.REVIEW),
        _decision("T010", "4410", [], Outcome.REVIEW),
    ]

    review = run_eval(decisions, repo).gates["review"]

    assert review.predicted == 2
    assert review.expected == 1
    assert review.correct == 1
    assert review.precision == 0.5
    assert review.recall == 1.0


def test_request_document_gate_counts_both_ground_truth_rows() -> None:
    repo = Repository()
    decisions = [
        _decision("T049", "0150", [], Outcome.REVIEW),
        _decision("T096", "0150", [], Outcome.REVIEW),
    ]

    request = run_eval(decisions, repo).gates["request_document"]

    assert request.expected == 2


def test_corrections_suppressed_yields_empty_and_never_mutates_seed() -> None:
    seed_path = SEEDS / "corrections.json"
    before = json.loads(seed_path.read_text())

    with corrections_suppressed() as cold_repo:
        assert cold_repo.corrections(CUSTOMER) == []

    after = json.loads(seed_path.read_text())
    assert after == before
    assert len(after) == 5


def test_moved_rows_detects_account_and_match_changes() -> None:
    cold = [
        _decision("T004", "4000", [], Outcome.REVIEW),
        _decision("T072", "1300", ["INV-2026-005"], Outcome.REVIEW),
        _decision("T100", "4300", [], Outcome.AUTO_POST),
    ]
    warm = [
        _decision("T004", "4300", [], Outcome.AUTO_POST),
        _decision("T072", "1300", ["INV-2026-004"], Outcome.REVIEW),
        _decision("T100", "4300", [], Outcome.AUTO_POST),
    ]

    assert moved_rows(cold, warm) == ["T004", "T072"]


def test_lift_report_measures_correction_gain_on_eligible_rows() -> None:
    repo = Repository()
    truth = repo.ground_truth()
    cold = [
        _decision("T004", "9999", [], Outcome.REVIEW),
        _decision("T099", "9999", [], Outcome.REVIEW),
    ]
    warm = [
        _decision("T004", truth["T004"].account, truth["T004"].match, Outcome.AUTO_POST),
        _decision("T099", truth["T099"].account, truth["T099"].match, Outcome.AUTO_POST),
    ]

    report = lift_report(cold, warm, repo)

    assert report.eligible_ids == ["T004", "T099"]
    assert report.cold_accuracy == 0.0
    assert report.corrected_accuracy == 1.0
    assert report.lift == 1.0


def test_lift_report_without_eligible_rows_leaves_lift_unset() -> None:
    repo = Repository()
    decisions = [_decision("T004", "4300", [], Outcome.REVIEW)]

    report = lift_report(decisions, decisions, repo)

    assert report.eligible_count == 0
    assert report.lift is None
    assert report.cold_categorization_accuracy == report.categorization_accuracy


def test_false_confidence_is_split_per_task_and_only_counts_auto_posts() -> None:
    repo = Repository()
    truth = repo.ground_truth()
    tid = "T001"
    right_account = truth[tid].account
    right_match = truth[tid].match
    wrong_account = "9999"
    wrong_match = ["__no_such_document__"]
    assert wrong_account != right_account
    assert set(wrong_match) != set(right_match)

    wrong_cat = run_eval([_decision(tid, wrong_account, right_match, Outcome.AUTO_POST)], repo)
    assert wrong_cat.false_confidence_categorization == 1
    assert wrong_cat.false_confidence_reconciliation == 0

    wrong_recon = run_eval([_decision(tid, right_account, wrong_match, Outcome.AUTO_POST)], repo)
    assert wrong_recon.false_confidence_categorization == 0
    assert wrong_recon.false_confidence_reconciliation == 1

    both_wrong = run_eval([_decision(tid, wrong_account, wrong_match, Outcome.AUTO_POST)], repo)
    assert both_wrong.false_confidence_categorization == 1
    assert both_wrong.false_confidence_reconciliation == 1

    fully_correct = run_eval([_decision(tid, right_account, right_match, Outcome.AUTO_POST)], repo)
    assert fully_correct.false_confidence_categorization == 0
    assert fully_correct.false_confidence_reconciliation == 0

    wrong_review = run_eval([_decision(tid, wrong_account, wrong_match, Outcome.REVIEW)], repo)
    assert wrong_review.false_confidence_categorization == 0
    assert wrong_review.false_confidence_reconciliation == 0

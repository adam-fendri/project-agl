from __future__ import annotations

from agl.models import (
    Anomaly,
    AnomalyType,
    Confidence,
    Decision,
    GroundTruth,
    MatchStatus,
    Outcome,
)
from scripts.run_eval import per_decision


def _decision(
    transaction_id: str,
    account: str,
    match: list[str],
    outcome: Outcome,
    anomaly: Anomaly | None = None,
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
        anomaly=anomaly,
        confidence_signals=[],
        outcome=outcome,
        sources=[],
    )


def _truth(transaction_id: str, account: str, match: list[str], outcome: Outcome) -> GroundTruth:
    return GroundTruth(transaction_id=transaction_id, account=account, match=match, outcome=outcome)


def test_per_decision_filters_to_truth_and_sorts_by_id() -> None:
    decisions = [
        _decision("T002", "4300", ["INV-1"], Outcome.AUTO_POST),
        _decision("T001", "9999", ["INV-1"], Outcome.AUTO_POST),
        _decision("T004", "4300", ["INV-9"], Outcome.AUTO_POST),
    ]
    truth = {
        "T001": _truth("T001", "4300", ["INV-1"], Outcome.AUTO_POST),
        "T002": _truth("T002", "4300", ["INV-1"], Outcome.AUTO_POST),
    }

    rows = per_decision(decisions, truth)

    assert [row["transaction_id"] for row in rows] == ["T001", "T002"]


def test_per_decision_flags_false_confidence_anomaly_fp_and_correct_row() -> None:
    decisions = [
        _decision("T001", "9999", ["INV-1"], Outcome.AUTO_POST),
        _decision("T002", "4300", ["INV-1"], Outcome.AUTO_POST),
        _decision(
            "T003",
            "4100",
            [],
            Outcome.ANOMALY,
            Anomaly(type=AnomalyType.DUPLICATE, reason="looks duplicated"),
        ),
    ]
    truth = {
        "T001": _truth("T001", "4300", ["INV-1"], Outcome.AUTO_POST),
        "T002": _truth("T002", "4300", ["INV-1"], Outcome.AUTO_POST),
        "T003": _truth("T003", "4100", [], Outcome.REVIEW),
    }

    by_id = {row["transaction_id"]: row for row in per_decision(decisions, truth)}

    wrong_account = by_id["T001"]
    assert wrong_account["account_correct"] is False
    assert wrong_account["false_confidence"] is True

    anomaly_fp = by_id["T003"]
    assert anomaly_fp["anomaly_false_positive"] is True
    assert anomaly_fp["anomaly"] == "duplicate"

    correct = by_id["T002"]
    assert correct["account_correct"] is True
    assert correct["match_correct"] is True
    assert correct["false_confidence"] is False
    assert correct["anomaly_false_positive"] is False

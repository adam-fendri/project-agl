from __future__ import annotations

import asyncio
import shutil
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from agl.engine import decide, finalize
from agl.models import (
    AgentProtocol,
    Decision,
    Evidence,
    GroundTruth,
    Outcome,
    Proposal,
    Transaction,
)
from agl.repository import SEEDS, Repository


class GateScore(BaseModel):
    """Precision and recall for one routing outcome, scored as a binary classifier against ground truth."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: str
    predicted: int
    expected: int
    correct: int
    precision: float
    recall: float


class EvalReport(BaseModel):
    """The eval result over a decision set scored against held-out ground truth.

    The categorization/match/false-confidence numbers and the per-outcome gates score the warm
    (corrections-applied) run. The lift fields, when populated, compare the cold (corrections-suppressed)
    run against the warm run on the eligible rows — the transactions a correction actually moved.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    categorization_accuracy: float
    match_accuracy: float
    false_confidence_count: int
    false_confidence_categorization: int = 0
    false_confidence_reconciliation: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    gates: dict[str, GateScore] = Field(default_factory=dict)
    cold_categorization_accuracy: float | None = None
    eligible_ids: list[str] = Field(default_factory=list)
    eligible_count: int = 0
    cold_accuracy: float | None = None
    corrected_accuracy: float | None = None
    lift: float | None = None


def _account_correct(decision: Decision, truth: GroundTruth) -> bool:
    return decision.account == truth.account


def _match_correct(decision: Decision, truth: GroundTruth) -> bool:
    return set(decision.match) == set(truth.match)


def _fully_correct(decision: Decision, truth: GroundTruth) -> bool:
    return _account_correct(decision, truth) and _match_correct(decision, truth)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _scored(decisions: list[Decision], truth: dict[str, GroundTruth]) -> list[tuple[Decision, GroundTruth]]:
    return [(d, truth[d.transaction_id]) for d in decisions if d.transaction_id in truth]


def _categorization_accuracy(decisions: list[Decision], truth: dict[str, GroundTruth]) -> float:
    scored = _scored(decisions, truth)
    return _ratio(sum(1 for d, g in scored if _account_correct(d, g)), len(scored))


def _gate(scored: list[tuple[Decision, GroundTruth]], outcome: Outcome) -> GateScore:
    predicted = sum(1 for d, _ in scored if d.outcome is outcome)
    expected = sum(1 for _, g in scored if g.outcome is outcome)
    correct = sum(1 for d, g in scored if d.outcome is outcome and g.outcome is outcome)
    return GateScore(
        outcome=outcome.value,
        predicted=predicted,
        expected=expected,
        correct=correct,
        precision=_ratio(correct, predicted),
        recall=_ratio(correct, expected),
    )


def run_eval(decisions: list[Decision], repo: Repository) -> EvalReport:
    """Score decisions against ground truth: categorization and match accuracy, false-confidence
    (auto-posted-and-wrong, target zero), per-outcome routing precision/recall (auto-post, review,
    anomaly, request-document), and the raw routing counts.
    """
    truth = repo.ground_truth()
    scored = _scored(decisions, truth)

    account_correct = sum(1 for d, g in scored if _account_correct(d, g))
    match_correct = sum(1 for d, g in scored if _match_correct(d, g))

    false_confidence = sum(
        1
        for d, g in scored
        if d.outcome is Outcome.AUTO_POST and not _fully_correct(d, g)
    )
    false_confidence_categorization = sum(
        1
        for d, g in scored
        if d.outcome is Outcome.AUTO_POST and not _account_correct(d, g)
    )
    false_confidence_reconciliation = sum(
        1
        for d, g in scored
        if d.outcome is Outcome.AUTO_POST and not _match_correct(d, g)
    )

    routed: dict[Outcome, int] = {outcome: 0 for outcome in Outcome}
    for d, _ in scored:
        routed[d.outcome] += 1

    gates = {outcome.value: _gate(scored, outcome) for outcome in Outcome}
    anomaly_gate = gates[Outcome.ANOMALY.value]

    counts = {
        "total": len(scored),
        "auto_post": routed[Outcome.AUTO_POST],
        "review": routed[Outcome.REVIEW],
        "anomaly": routed[Outcome.ANOMALY],
        "request_document": routed[Outcome.REQUEST_DOCUMENT],
        "categorization_correct": account_correct,
        "match_correct": match_correct,
        "false_confidence_categorization": false_confidence_categorization,
        "false_confidence_reconciliation": false_confidence_reconciliation,
        "anomalies_expected": anomaly_gate.expected,
        "anomalies_caught": anomaly_gate.correct,
        "anomaly_false_positives": anomaly_gate.predicted - anomaly_gate.correct,
    }

    return EvalReport(
        categorization_accuracy=_ratio(account_correct, len(scored)),
        match_accuracy=_ratio(match_correct, len(scored)),
        false_confidence_count=false_confidence,
        false_confidence_categorization=false_confidence_categorization,
        false_confidence_reconciliation=false_confidence_reconciliation,
        counts=counts,
        gates=gates,
    )


def moved_rows(cold: list[Decision], corrected: list[Decision]) -> list[str]:
    """The transactions a correction changed: same id, different account or different matched documents."""
    cold_by = {d.transaction_id: d for d in cold}
    moved: list[str] = []
    for warm in corrected:
        prior = cold_by.get(warm.transaction_id)
        if prior is None:
            continue
        if prior.account != warm.account or set(prior.match) != set(warm.match):
            moved.append(warm.transaction_id)
    return moved


def lift_report(
    cold: list[Decision],
    corrected: list[Decision],
    repo: Repository,
    eligible_ids: list[str] | None = None,
) -> EvalReport:
    """Score the corrected run and attach the cold-vs-corrected lift on the eligible rows.

    Eligible rows default to the transactions a correction actually moved (``moved_rows``); the lift
    is the gain in fully-correct (account and match) entries on exactly those rows, so it measures
    whether a correction improves its own siblings rather than washing out in the untouched majority.
    """
    truth = repo.ground_truth()
    base = run_eval(corrected, repo)

    eligible = eligible_ids if eligible_ids is not None else moved_rows(cold, corrected)
    eligible_set = set(eligible)

    cold_eligible = [(d, truth[d.transaction_id]) for d in cold if d.transaction_id in eligible_set and d.transaction_id in truth]
    warm_eligible = [(d, truth[d.transaction_id]) for d in corrected if d.transaction_id in eligible_set and d.transaction_id in truth]

    cold_accuracy = _ratio(sum(1 for d, g in cold_eligible if _fully_correct(d, g)), len(cold_eligible))
    corrected_accuracy = _ratio(sum(1 for d, g in warm_eligible if _fully_correct(d, g)), len(warm_eligible))

    return base.model_copy(
        update={
            "cold_categorization_accuracy": _categorization_accuracy(cold, truth),
            "eligible_ids": sorted(eligible_set),
            "eligible_count": len(eligible_set),
            "cold_accuracy": cold_accuracy if eligible_set else None,
            "corrected_accuracy": corrected_accuracy if eligible_set else None,
            "lift": (corrected_accuracy - cold_accuracy) if eligible_set else None,
        }
    )


@contextmanager
def corrections_suppressed(seeds_dir: Path = SEEDS) -> Generator[Repository, None, None]:
    """A Repository over a copy of the seeds with the prior corrections removed, for the cold run.

    The committed ``seeds/`` is never touched: every seed file is copied to a temp directory,
    ``corrections.json`` is overwritten with an empty list, and the runtime store points at a fresh
    empty directory so no learned corrections leak into the cold baseline.
    """
    with tempfile.TemporaryDirectory() as seeds_tmp, tempfile.TemporaryDirectory() as runtime_tmp:
        cold_seeds = Path(seeds_tmp)
        for seed_file in seeds_dir.glob("*.json"):
            shutil.copy(seed_file, cold_seeds / seed_file.name)
        (cold_seeds / "corrections.json").write_text("[]")
        yield Repository(seeds_dir=cold_seeds, runtime_dir=Path(runtime_tmp))


@dataclass(frozen=True)
class BatchResult:
    decisions: list[Decision]
    failed: list[str]


class LiftHarness:
    """Runs the batch twice — corrections suppressed (cold) then applied (warm) — to measure learning lift.

    Each batch is two-pass: PASS 1 decides every transaction concurrently (bounded by the semaphore,
    with per-transaction retries), then ``settled_by`` is resolved over the full set of matches and PASS 2
    finalizes each transaction. A duplicate is the later claimant of a shared document, independent of
    processing order. Per-transaction agent failures are retried and then recorded, never aborting the run.
    """

    def __init__(
        self,
        repo: Repository,
        agent: AgentProtocol,
        customer_id: str,
        seeds_dir: Path = SEEDS,
        concurrency: int = 4,
        retries: int = 2,
    ) -> None:
        self._repo = repo
        self._agent = agent
        self._customer = customer_id
        self._seeds_dir = seeds_dir
        self._concurrency = concurrency
        self._retries = retries

    async def cold_and_warm(self, subset: set[str] | None = None) -> tuple[BatchResult, BatchResult]:
        warm = await self._batch(self._repo, subset)
        with corrections_suppressed(self._seeds_dir) as cold_repo:
            cold = await self._batch(cold_repo, subset)
        return cold, warm

    async def _batch(self, repo: Repository, subset: set[str] | None) -> BatchResult:
        selected = [t for t in repo.transactions(self._customer) if subset is None or t.id in subset]
        semaphore = asyncio.Semaphore(self._concurrency)

        async def _bounded(txn: Transaction) -> tuple[Evidence, Proposal] | None:
            async with semaphore:
                return await self._decide_one(repo, txn)

        decided = await asyncio.gather(*(_bounded(txn) for txn in selected))

        settled_by: dict[str, list[str]] = {}
        for txn, item in zip(selected, decided, strict=True):
            if item is None:
                continue
            _evidence, proposal = item
            for doc_id in proposal.match:
                settled_by.setdefault(doc_id, []).append(txn.id)

        decisions: list[Decision] = []
        failed: list[str] = []
        for txn, item in zip(selected, decided, strict=True):
            if item is None:
                failed.append(txn.id)
                continue
            evidence, proposal = item
            decisions.append(finalize(txn, repo, evidence, proposal, settled_by))
        return BatchResult(decisions=decisions, failed=failed)

    async def _decide_one(
        self, repo: Repository, txn: Transaction
    ) -> tuple[Evidence, Proposal] | None:
        for attempt in range(self._retries + 1):
            try:
                return await decide(txn, repo, self._agent)
            except Exception:
                if attempt == self._retries:
                    return None
        return None

from __future__ import annotations

import asyncio

import pytest

from agl.engine import run_batch
from agl.models import AgentProtocol, Confidence, Decision, Evidence, Outcome, Proposal
from agl.repository import Repository

CUSTOMER = "studio-vondel"


@pytest.fixture(scope="module")
def repo() -> Repository:
    return Repository()


class _ScriptedAgent:
    """A no-LLM agent: returns a fixed account/match for the named transactions, abstains on the rest."""

    def __init__(self, matches: dict[str, list[str]], accounts: dict[str, str]) -> None:
        self._matches = matches
        self._accounts = accounts

    async def decide(self, evidence: Evidence) -> Proposal:
        txn = evidence.transaction
        if txn.id in self._accounts:
            match = self._matches.get(txn.id, [])
            return Proposal(
                vendor=txn.counterparty,
                account=self._accounts[txn.id],
                account_reasoning="scripted",
                account_confidence=Confidence.HIGH,
                match=match,
                match_reasoning="scripted" if match else None,
                match_confidence=Confidence.HIGH,
            )
        return Proposal(
            vendor=txn.counterparty,
            account=evidence.accounts[0].number,
            account_reasoning="scripted",
            account_confidence=Confidence.LOW,
            match=[],
            match_reasoning=None,
            match_confidence=Confidence.LOW,
        )


class _UnlistedAgent:
    """A no-LLM agent: one HIGH/HIGH documentless proposal for the target, account_unlisted toggled, others abstain."""

    def __init__(self, target: str, vendor: str, account: str, account_unlisted: bool) -> None:
        self._target = target
        self._vendor = vendor
        self._account = account
        self._account_unlisted = account_unlisted

    async def decide(self, evidence: Evidence) -> Proposal:
        txn = evidence.transaction
        if txn.id == self._target:
            return Proposal(
                vendor=self._vendor,
                account=self._account,
                account_reasoning="scripted",
                account_confidence=Confidence.HIGH,
                account_unlisted=self._account_unlisted,
                match=[],
                match_reasoning=None,
                match_confidence=Confidence.HIGH,
            )
        return Proposal(
            vendor=txn.counterparty,
            account=evidence.accounts[0].number,
            account_reasoning="scripted",
            account_confidence=Confidence.LOW,
            match=[],
            match_reasoning=None,
            match_confidence=Confidence.LOW,
        )


class _FlakyAgent:
    """Raises for one transaction (a hard agent failure), returns a normal proposal for a second, abstains on the rest."""

    def __init__(self, failing: str, ok: str, account: str) -> None:
        self._failing = failing
        self._ok = ok
        self._account = account

    async def decide(self, evidence: Evidence) -> Proposal:
        txn = evidence.transaction
        if txn.id == self._failing:
            raise RuntimeError("simulated agent failure")
        if txn.id == self._ok:
            return Proposal(
                vendor=txn.counterparty,
                account=self._account,
                account_reasoning="scripted",
                account_confidence=Confidence.HIGH,
                match=[],
                match_reasoning=None,
                match_confidence=Confidence.HIGH,
            )
        return Proposal(
            vendor=txn.counterparty,
            account=evidence.accounts[0].number,
            account_reasoning="scripted",
            account_confidence=Confidence.LOW,
            match=[],
            match_reasoning=None,
            match_confidence=Confidence.LOW,
        )


def _decisions(agent: AgentProtocol, repo: Repository) -> dict[str, Decision]:
    return {d.transaction_id: d for d in asyncio.run(run_batch(repo, agent, CUSTOMER))}


def test_duplicate_later_transaction_is_anomaly_independent_of_order(repo: Repository) -> None:
    agent = _ScriptedAgent(
        matches={"T040": ["B-11"], "T046": ["B-11"]},
        accounts={"T040": "4100", "T046": "4100"},
    )
    decisions = _decisions(agent, repo)

    later = decisions["T046"]
    earlier = decisions["T040"]

    assert later.outcome is Outcome.ANOMALY
    assert "guard:duplicate:B-11" in later.confidence_signals
    assert earlier.outcome is not Outcome.ANOMALY
    assert "guard:duplicate:B-11" not in earlier.confidence_signals


def test_swap_to_different_same_amount_invoices_is_not_duplicate(repo: Repository) -> None:
    agent = _ScriptedAgent(
        matches={"T072": ["INV-2026-004"], "T074": ["INV-2026-005"]},
        accounts={"T072": "1300", "T074": "1300"},
    )
    decisions = _decisions(agent, repo)

    for tid in ("T072", "T074"):
        signals = decisions[tid].confidence_signals
        assert not any(s.startswith("guard:duplicate:") for s in signals)


def test_account_unlisted_downgrades_auto_post_to_review(repo: Repository) -> None:
    unlisted = _UnlistedAgent("T062", "AWS", "4310", account_unlisted=True)
    listed = _UnlistedAgent("T062", "AWS", "4310", account_unlisted=False)

    flagged = _decisions(unlisted, repo)["T062"]
    normal = _decisions(listed, repo)["T062"]

    assert flagged.account_unlisted is True
    assert flagged.outcome is Outcome.REVIEW
    assert "account_unlisted" in flagged.confidence_signals
    assert "guard:account_unlisted" in flagged.confidence_signals
    assert normal.account_unlisted is False
    assert normal.outcome is Outcome.AUTO_POST


def test_unverified_high_confidence_categorisation_auto_posts(repo: Repository) -> None:
    agent = _ScriptedAgent(matches={}, accounts={"T006": "4300"})

    decision = _decisions(agent, repo)["T006"]

    assert decision.account_confidence is Confidence.HIGH
    assert decision.match == []
    assert decision.outcome is Outcome.AUTO_POST
    assert "account_unverified" in decision.confidence_signals


def test_bill_verified_categorisation_auto_posts(repo: Repository) -> None:
    agent = _ScriptedAgent(matches={"T029": ["B-07"]}, accounts={"T029": "4310"})

    decision = _decisions(agent, repo)["T029"]

    assert decision.outcome is Outcome.AUTO_POST
    assert "account_verified" in decision.confidence_signals


def test_agent_failure_fails_closed_to_review_without_aborting_batch(repo: Repository) -> None:
    agent = _FlakyAgent(failing="T006", ok="T003", account="4300")

    decisions = _decisions(agent, repo)

    failed = decisions["T006"]
    assert failed.outcome is Outcome.REVIEW
    assert failed.account_confidence is Confidence.LOW
    assert "agent_error" in failed.confidence_signals

    assert decisions["T003"].outcome is Outcome.AUTO_POST
    assert len(decisions) == len(repo.transactions(CUSTOMER))


def test_decision_carries_vat_treatment_from_account(repo: Repository) -> None:
    agent = _ScriptedAgent(matches={}, accounts={"T003": "4300", "T005": "4600"})

    decisions = _decisions(agent, repo)

    assert decisions["T003"].vat_treatment == "standard"
    assert decisions["T005"].vat_treatment == "reduced"

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


def test_unverified_high_confidence_categorisation_downgrades_to_review(repo: Repository) -> None:
    agent = _ScriptedAgent(matches={}, accounts={"T006": "4300"})

    decision = _decisions(agent, repo)["T006"]

    assert decision.account_confidence is Confidence.HIGH
    assert decision.match == []
    assert decision.outcome is Outcome.REVIEW
    assert "account_unverified" in decision.confidence_signals


def test_bill_verified_categorisation_auto_posts(repo: Repository) -> None:
    agent = _ScriptedAgent(matches={"T029": ["B-07"]}, accounts={"T029": "4310"})

    decision = _decisions(agent, repo)["T029"]

    assert decision.outcome is Outcome.AUTO_POST
    assert "account_verified" in decision.confidence_signals

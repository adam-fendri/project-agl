from __future__ import annotations

import asyncio

import pytest

from agl.engine import run_batch
from agl.models import Confidence, Decision, Evidence, Outcome, Proposal
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


def _decisions(agent: _ScriptedAgent, repo: Repository) -> dict[str, Decision]:
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

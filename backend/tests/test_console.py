from __future__ import annotations

import asyncio
from collections import defaultdict
from pathlib import Path

from agl.api import AssignAccountRequest, Console, CreateAccountRequest
from agl.learning import canonical_vendor, vendor_cost_account
from agl.models import Confidence, Evidence, Proposal, Rubriek
from agl.repository import Repository

CUSTOMER = "studio-vondel"


class _ScriptedAgent:
    """A no-LLM agent that follows a prior correction for the vendor as the real agent does, else returns a scripted account at a fixed confidence."""

    def __init__(self, accounts: dict[str, str], confidence: Confidence = Confidence.LOW) -> None:
        self._accounts = accounts
        self._confidence = confidence

    async def decide(self, evidence: Evidence) -> Proposal:
        txn = evidence.transaction
        corrected = vendor_cost_account(
            canonical_vendor(txn), evidence.corrections, evidence.accounts
        )
        account = corrected or self._accounts.get(txn.id, evidence.accounts[0].number)
        confidence = Confidence.HIGH if corrected else self._confidence
        return Proposal(
            vendor=txn.counterparty,
            account=account,
            account_reasoning="scripted",
            account_confidence=confidence,
            match=[],
            match_reasoning=None,
            match_confidence=Confidence.HIGH,
        )


def _console(agent: _ScriptedAgent, runtime_dir: Path) -> Console:
    return Console(Repository(runtime_dir=runtime_dir), agent, CUSTOMER)


def _same_vendor_pair() -> tuple[str, str]:
    by_vendor: dict[str, list[str]] = defaultdict(list)
    for txn in Repository().transactions(CUSTOMER):
        by_vendor[canonical_vendor(txn)].append(txn.id)
    for ids in by_vendor.values():
        if len(ids) >= 2:
            return ids[0], ids[1]
    raise AssertionError("no vendor with two transactions in the seed data")


def test_run_then_accept_posts(tmp_path: Path) -> None:
    console = _console(_ScriptedAgent(accounts={}, confidence=Confidence.LOW), tmp_path)
    asyncio.run(console.run())

    review = console.queue()
    assert review, "low-confidence scripted decisions should populate the review queue"

    target = review[0].transaction_id
    console.accept(target)
    assert any(d.transaction_id == target for d in console.posted())


def test_correct_applies_account_and_moves_same_vendor_sibling(tmp_path: Path) -> None:
    first, sibling = _same_vendor_pair()
    console = _console(_ScriptedAgent(accounts={first: "4900", sibling: "4900"}), tmp_path)
    asyncio.run(console.run())

    response = asyncio.run(console.correct(first, corrected_account="4300", corrected_match=None))

    assert response.correction_id
    assert sibling in response.reran
    assert console.decision(first).account == "4300"
    assert console.decision(sibling).account == "4300"


def test_create_and_assign_new_account(tmp_path: Path) -> None:
    target, _ = _same_vendor_pair()
    console = _console(_ScriptedAgent(accounts={target: "4900"}), tmp_path)
    asyncio.run(console.run())

    asyncio.run(
        console.create_account(
            CreateAccountRequest(
                number="4999", name_en="Staff catering", name_nl="Personeelscatering", rubriek=Rubriek.COSTS
            )
        )
    )
    asyncio.run(console.assign_account(target, AssignAccountRequest(number="4999")))

    assert console.decision(target).account == "4999"


def test_trace_returns_the_decision_and_prompt(tmp_path: Path) -> None:
    target, _ = _same_vendor_pair()
    console = _console(_ScriptedAgent(accounts={target: "4900"}), tmp_path)
    asyncio.run(console.run())

    trace = console.trace(target)
    assert trace.decision.transaction_id == target
    assert trace.prompt

from __future__ import annotations

from decimal import Decimal

from agl.grounding import build_evidence, counterparty_agrees, party_of
from agl.guard import run_guard
from agl.models import (
    AgentProtocol,
    AnomalyType,
    Confidence,
    Decision,
    Evidence,
    GuardVerdict,
    MatchStatus,
    Outcome,
    Proposal,
    Transaction,
)
from agl.reconcile import validate_match
from agl.repository import Repository

_SEVERITY: dict[Outcome, int] = {
    Outcome.AUTO_POST: 0,
    Outcome.REVIEW: 1,
    Outcome.REQUEST_DOCUMENT: 2,
    Outcome.ANOMALY: 3,
}

_MATERIAL_EUR = Decimal("1000")


async def process(
    txn: Transaction,
    repo: Repository,
    agent: AgentProtocol,
    claimed_by: dict[str, list[str]],
) -> Decision:
    """Run one transaction through ground -> decide -> guard -> route, producing a Decision."""
    evidence = build_evidence(txn, repo, txn.customer_id, claimed_by)
    proposal = await agent.decide(evidence)
    verdict = run_guard(proposal, txn, repo, claimed_by)
    return _assemble(txn, repo, evidence, proposal, verdict)


async def run_batch(repo: Repository, agent: AgentProtocol, customer_id: str) -> list[Decision]:
    """Process every transaction in date order, accumulating the resolved-settlement collision map.

    ``claimed_by`` holds resolved settlements (what earlier decisions actually settled): each
    transaction is decided against only earlier decisions' matches, never its own provided prior.
    """
    claimed_by: dict[str, list[str]] = {}
    decisions: list[Decision] = []
    for txn in sorted(repo.transactions(customer_id), key=lambda t: (t.booked_on, t.id)):
        decision = await process(txn, repo, agent, claimed_by)
        decisions.append(decision)
        for doc_id in decision.match:
            claimed_by.setdefault(doc_id, []).append(decision.transaction_id)
    return decisions


def _assemble(
    txn: Transaction,
    repo: Repository,
    evidence: Evidence,
    proposal: Proposal,
    verdict: GuardVerdict,
) -> Decision:
    match_status = _match_status(txn, repo, proposal.match)
    return Decision(
        transaction_id=txn.id,
        vendor=proposal.vendor,
        account=proposal.account,
        account_reasoning=proposal.account_reasoning,
        account_confidence=proposal.account_confidence,
        match=list(proposal.match),
        match_reasoning=proposal.match_reasoning,
        match_status=match_status,
        match_confidence=proposal.match_confidence,
        anomaly=proposal.anomaly,
        confidence_signals=_confidence_signals(
            txn, repo, evidence, proposal, verdict, match_status
        ),
        outcome=_route(txn, repo, proposal, verdict),
        sources=_sources(evidence, proposal),
    )


def _match_status(txn: Transaction, repo: Repository, match: list[str]) -> MatchStatus:
    if not match:
        return MatchStatus.NONE
    verdict = validate_match(
        txn,
        match,
        {i.id: i for i in repo.invoices(txn.customer_id)},
        {b.id: b for b in repo.bills(txn.customer_id)},
    )
    if verdict.sums_exactly and verdict.direction_ok:
        return MatchStatus.FULL
    return MatchStatus.PARTIAL


def _route(
    txn: Transaction, repo: Repository, proposal: Proposal, verdict: GuardVerdict
) -> Outcome:
    intended = _intended_outcome(proposal)
    if intended is Outcome.AUTO_POST and _material_uncorroborated(txn, repo, proposal):
        intended = Outcome.REVIEW
    if verdict.passed or verdict.forced_outcome is None:
        return intended
    return max(intended, verdict.forced_outcome, key=lambda outcome: _SEVERITY[outcome])


def _material_uncorroborated(txn: Transaction, repo: Repository, proposal: Proposal) -> bool:
    if abs(txn.amount) < _MATERIAL_EUR or not proposal.match:
        return False
    documents = [doc for did in proposal.match if (doc := repo.document(did)) is not None]
    if not documents or not any(doc.vat != 0 for doc in documents):
        return False
    return not all(counterparty_agrees(party_of(doc), txn) for doc in documents)


def _intended_outcome(proposal: Proposal) -> Outcome:
    anomaly = proposal.anomaly
    if anomaly is not None:
        if anomaly.type is AnomalyType.MISSING_COUNTERPART:
            return Outcome.REQUEST_DOCUMENT
        return Outcome.ANOMALY
    if (
        proposal.account_confidence is Confidence.HIGH
        and proposal.match_confidence is Confidence.HIGH
    ):
        return Outcome.AUTO_POST
    return Outcome.REVIEW


def _confidence_signals(
    txn: Transaction,
    repo: Repository,
    evidence: Evidence,
    proposal: Proposal,
    verdict: GuardVerdict,
    match_status: MatchStatus,
) -> list[str]:
    signals: list[str] = []
    if proposal.account in {a.number for a in evidence.accounts}:
        signals.append("account_in_chart")
    else:
        signals.append("account_not_in_chart")

    if proposal.match:
        signals.append(
            "amount_sums_exactly" if match_status is MatchStatus.FULL else "amount_not_exact"
        )
        provided = repo.provided_match(txn.id)
        if provided is None:
            signals.append("match_without_provided")
        elif provided.document_id in proposal.match:
            signals.append("provided_match_confirmed")
        else:
            signals.append("provided_match_overridden")
    else:
        signals.append("no_match")

    if evidence.duplicate_note is not None:
        signals.append("duplicate_collision")
    signals.extend(f"guard:{check}" for check in verdict.failed_checks)
    return signals


def _sources(evidence: Evidence, proposal: Proposal) -> list[str]:
    sources: list[str] = [f"account:{proposal.account}"]
    sources.extend(f"document:{doc_id}" for doc_id in proposal.match)
    sources.extend(f"correction:{correction.id}" for correction in evidence.corrections)
    return sources

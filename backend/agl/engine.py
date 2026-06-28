from __future__ import annotations

import asyncio
from decimal import Decimal

from agl.grounding import (
    build_evidence,
    counterparty_agrees,
    party_of,
    realised_vat_rate,
    referenced_documents,
    treatment_rate,
)
from agl.guard import run_guard
from agl.learning import canonical_vendor, vendor_cost_account
from agl.models import (
    AgentProtocol,
    AnomalyType,
    Bill,
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


_CONCURRENCY = 8


async def decide(
    txn: Transaction, repo: Repository, agent: AgentProtocol
) -> tuple[Evidence, Proposal]:
    """Ground the transaction and ask the agent to decide it, independently of every other one.

    No duplicate hint reaches the agent: a duplicate is a cross-transaction fact resolved later from
    the full set of matches, so this pass carries no shared state and assumes no processing order.
    """
    evidence = build_evidence(txn, repo, txn.customer_id)
    proposal = await agent.decide(evidence)
    return evidence, proposal


def finalize(
    txn: Transaction,
    repo: Repository,
    evidence: Evidence,
    proposal: Proposal,
    settled_by: dict[str, list[str]],
) -> Decision:
    """Guard the proposal against the full resolved-settlement map, then assemble the Decision."""
    verdict = run_guard(proposal, txn, repo, settled_by)
    return _assemble(txn, repo, evidence, proposal, verdict)


async def run_batch(repo: Repository, agent: AgentProtocol, customer_id: str) -> list[Decision]:
    """Decide every transaction concurrently, then finalize each against the full settlement map.

    PASS 1 grounds and decides each transaction independently, bounded by a semaphore, with no shared
    state. PASS 2 builds ``settled_by`` (doc id -> the transaction ids that matched it) over every
    proposal, then finalizes each transaction, so a duplicate is the later claimant of a shared
    document regardless of processing order. Decisions are returned in input order; there is no sort.
    """
    transactions = repo.transactions(customer_id)
    semaphore = asyncio.Semaphore(_CONCURRENCY)

    async def _bounded(txn: Transaction) -> tuple[Transaction, Evidence, Proposal]:
        async with semaphore:
            evidence, proposal = await decide(txn, repo, agent)
            return txn, evidence, proposal

    decided = await asyncio.gather(*(_bounded(txn) for txn in transactions))

    settled_by: dict[str, list[str]] = {}
    for txn, _evidence, proposal in decided:
        for doc_id in proposal.match:
            settled_by.setdefault(doc_id, []).append(txn.id)

    return [
        finalize(txn, repo, evidence, proposal, settled_by)
        for txn, evidence, proposal in decided
    ]


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
        account_unlisted=proposal.account_unlisted,
        match=list(proposal.match),
        match_reasoning=proposal.match_reasoning,
        match_status=match_status,
        match_confidence=proposal.match_confidence,
        anomaly=proposal.anomaly,
        confidence_signals=_confidence_signals(
            txn, repo, evidence, proposal, verdict, match_status
        ),
        outcome=_route(txn, repo, evidence, proposal, verdict),
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
    txn: Transaction,
    repo: Repository,
    evidence: Evidence,
    proposal: Proposal,
    verdict: GuardVerdict,
) -> Outcome:
    intended = _intended_outcome(proposal)
    if intended is Outcome.AUTO_POST and _material_uncorroborated(txn, repo, proposal):
        intended = Outcome.REVIEW
    if intended is Outcome.AUTO_POST and not _categorisation_verified(
        txn, repo, evidence, proposal
    ):
        intended = Outcome.REVIEW
    if verdict.passed or verdict.forced_outcome is None:
        return intended
    return max(intended, verdict.forced_outcome, key=lambda outcome: _SEVERITY[outcome])


def _categorisation_verified(
    txn: Transaction, repo: Repository, evidence: Evidence, proposal: Proposal
) -> bool:
    """A fact, not the model's confidence, corroborates the proposed account.

    Any one suffices: the vendor recurs as an established counterparty, a prior correction pins this
    vendor's cost account, an earlier transaction for the same vendor was booked there, a settling bill
    is already booked there, or a settled document's realised VAT rate matches the account's treatment.
    Absent all of these, an auto-post is deferred to review — a wrong categorisation otherwise surfaces
    only at period-end.
    """
    if _recurring_vendor(txn, repo):
        return True
    if (
        vendor_cost_account(canonical_vendor(txn), evidence.corrections, evidence.accounts)
        == proposal.account
    ):
        return True
    if any(entry.account == proposal.account for entry in evidence.vendor_history):
        return True
    for did in proposal.match:
        doc = repo.document(did)
        if isinstance(doc, Bill) and doc.account == proposal.account:
            return True
    treatment = {a.number: a.vat_treatment for a in evidence.accounts}.get(proposal.account)
    if treatment is None:
        return False
    expected = treatment_rate(treatment)
    for did in proposal.match:
        doc = repo.document(did)
        if doc is None or doc.net == 0:
            continue
        if realised_vat_rate(doc) == expected:
            return True
    return False


def _recurring_vendor(txn: Transaction, repo: Repository) -> bool:
    """The vendor is an established, recurring counterparty, so a categorisation on a repeat is reliable."""
    vendor = canonical_vendor(txn)
    occurrences = sum(
        1 for other in repo.transactions(txn.customer_id) if canonical_vendor(other) == vendor
    )
    return occurrences >= 3


def _material_uncorroborated(txn: Transaction, repo: Repository, proposal: Proposal) -> bool:
    if abs(txn.amount) < _MATERIAL_EUR or not proposal.match:
        return False
    documents = [doc for did in proposal.match if (doc := repo.document(did)) is not None]
    if not documents or not any(doc.vat != 0 for doc in documents):
        return False
    known_ids = {i.id for i in repo.invoices(txn.customer_id)} | {
        b.id for b in repo.bills(txn.customer_id)
    }
    if set(referenced_documents(txn, known_ids)) & set(proposal.match):
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

    if proposal.account_unlisted:
        signals.append("account_unlisted")

    if _categorisation_verified(txn, repo, evidence, proposal):
        signals.append("account_verified")
    else:
        signals.append("account_unverified")

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

    signals.extend(f"guard:{check}" for check in verdict.failed_checks)
    return signals


def _sources(evidence: Evidence, proposal: Proposal) -> list[str]:
    sources: list[str] = [f"account:{proposal.account}"]
    sources.extend(f"document:{doc_id}" for doc_id in proposal.match)
    sources.extend(f"correction:{correction.id}" for correction in evidence.corrections)
    return sources

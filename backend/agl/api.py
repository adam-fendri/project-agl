from __future__ import annotations

import asyncio
import os
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agl.agent import ClaudeCliAgent, LlmAgent
from agl.engine import process, run_batch
from agl.eval import EvalReport, run_eval
from agl.grounding import build_evidence, render_prompt
from agl.guard import run_guard
from agl.learning import apply_correction, pending_reruns
from agl.models import (
    AgentProtocol,
    Confidence,
    Decision,
    Evidence,
    Outcome,
    Proposal,
    Rubriek,
    Trace,
    Transaction,
)
from agl.repository import Repository

_DEFAULT_CUSTOMER = "studio-vondel"

_RISK: dict[Confidence, float] = {Confidence.HIGH: 0.1, Confidence.MEDIUM: 0.5, Confidence.LOW: 0.9}
_VAT_SENSITIVE: set[Rubriek] = {Rubriek.COSTS, Rubriek.REVENUE}
_VAT_WEIGHT = 1.25

_OUTCOME_NARRATION: dict[Outcome, str] = {
    Outcome.AUTO_POST: "Both confidences are high and the guard passed, so this auto-posts.",
    Outcome.REVIEW: "A confidence is below high or the guard downgraded it, so it is deferred for review.",
    Outcome.ANOMALY: "It is routed to the anomaly queue for the accountant to resolve.",
    Outcome.REQUEST_DOCUMENT: "A material document is missing, so the entrepreneur is asked to provide it.",
}


class CorrectRequest(BaseModel):
    corrected_account: str | None = None
    corrected_match: list[str] | None = None


class CorrectResponse(BaseModel):
    correction_id: str
    reran: list[str]


class ExplainResponse(BaseModel):
    transaction_id: str
    explanation: str


def _select_agent() -> AgentProtocol:
    choice = os.getenv("AGL_AGENT", "").strip().lower()
    if choice == "llm" or any(
        os.getenv(key) for key in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
    ):
        return LlmAgent()
    return ClaudeCliAgent()


def _proposal_from_decision(decision: Decision) -> Proposal:
    return Proposal(
        vendor=decision.vendor,
        account=decision.account,
        account_reasoning=decision.account_reasoning,
        account_confidence=decision.account_confidence,
        match=list(decision.match),
        match_reasoning=decision.match_reasoning,
        match_confidence=decision.match_confidence,
        anomaly=decision.anomaly,
    )


def _context(evidence: Evidence) -> dict[str, object]:
    txn = evidence.transaction
    transaction: dict[str, str] = {
        "id": txn.id,
        "booked_on": txn.booked_on.isoformat(),
        "amount": str(txn.amount),
        "type": txn.type.value,
        "counterparty": txn.counterparty,
        "description": txn.description,
    }
    provided = evidence.provided_match
    context: dict[str, object] = {
        "transaction": transaction,
        "accounts_available": len(evidence.accounts),
        "provided_match": list(provided.candidate.document_ids) if provided is not None else None,
        "candidates": [list(fact.candidate.document_ids) for fact in evidence.candidates],
        "corrections": [correction.id for correction in evidence.corrections],
        "vendor_history": [entry.transaction_id for entry in evidence.vendor_history],
        "duplicate_note": evidence.duplicate_note,
    }
    return context


def _narrate(decision: Decision) -> str:
    lines: list[str] = [
        f"{decision.vendor} was categorized to account {decision.account} "
        f"({decision.account_reasoning}); account confidence {decision.account_confidence.value}.",
    ]
    if decision.match:
        reasoning = decision.match_reasoning or "no reasoning given"
        lines.append(
            f"It settles {', '.join(decision.match)} ({reasoning}); the matched amount is "
            f"{decision.match_status.value}, match confidence {decision.match_confidence.value}."
        )
    else:
        lines.append("No document in the system settles this transaction.")
    if decision.anomaly is not None:
        lines.append(f"Anomaly flagged ({decision.anomaly.type.value}): {decision.anomaly.reason}.")
    lines.append(_OUTCOME_NARRATION[decision.outcome])
    if decision.confidence_signals:
        lines.append(f"Verified signals: {', '.join(decision.confidence_signals)}.")
    return " ".join(lines)


def _rank_key(
    decision: Decision,
    amounts: dict[str, Decimal],
    rubrieks: dict[str, Rubriek],
) -> tuple[bool, float]:
    amount = float(abs(amounts.get(decision.transaction_id, Decimal("0"))))
    weight = _VAT_WEIGHT if rubrieks.get(decision.account) in _VAT_SENSITIVE else 1.0
    uncertainty = max(_RISK[decision.account_confidence], _RISK[decision.match_confidence])
    score = amount * weight * uncertainty
    return (decision.outcome is not Outcome.ANOMALY, -score)


class Console:
    """Stateful API surface over the engine: holds the run's decisions, the posted set, and the learning loop."""

    def __init__(self, repo: Repository, agent: AgentProtocol, customer_id: str) -> None:
        self._repo = repo
        self._agent = agent
        self._customer = customer_id
        self._decisions: dict[str, Decision] = {}
        self._posted: set[str] = set()
        self._lock = asyncio.Lock()

    @classmethod
    def create(cls) -> Console:
        return cls(Repository(), _select_agent(), os.getenv("AGL_CUSTOMER", _DEFAULT_CUSTOMER))

    async def run(self) -> list[Decision]:
        async with self._lock:
            decisions = await run_batch(self._repo, self._agent, self._customer)
            self._decisions = {decision.transaction_id: decision for decision in decisions}
            self._posted.clear()
            return decisions

    def queue(self) -> list[Decision]:
        deferred = [
            decision
            for decision in self._decisions.values()
            if decision.outcome is not Outcome.AUTO_POST and decision.transaction_id not in self._posted
        ]
        amounts = {txn.id: txn.amount for txn in self._repo.transactions(self._customer)}
        rubrieks = {account.number: account.rubriek for account in self._repo.accounts(self._customer)}
        return sorted(deferred, key=lambda decision: _rank_key(decision, amounts, rubrieks))

    def decision(self, txn_id: str) -> Decision:
        found = self._decisions.get(txn_id)
        if found is None:
            raise HTTPException(status_code=404, detail=f"no decision for {txn_id}; run the engine first")
        return found

    def accept(self, txn_id: str) -> Decision:
        found = self.decision(txn_id)
        self._posted.add(txn_id)
        return found

    def posted(self) -> list[Decision]:
        return [
            decision
            for decision in self._decisions.values()
            if decision.outcome is Outcome.AUTO_POST or decision.transaction_id in self._posted
        ]

    async def correct(
        self,
        txn_id: str,
        corrected_account: str | None,
        corrected_match: list[str] | None,
    ) -> CorrectResponse:
        async with self._lock:
            decision = self.decision(txn_id)
            try:
                correction = apply_correction(
                    self._repo, txn_id, corrected_account, corrected_match, vendor=decision.vendor
                )
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e)) from e
            self._repo = self._repo.reload()
            reran = pending_reruns(correction, list(self._decisions.values()))
            for affected in [txn_id, *reran]:
                txn = self._find(affected)
                if txn is None:
                    continue
                claimed_by = self._resolved_claims(exclude=affected)
                self._decisions[affected] = await process(txn, self._repo, self._agent, claimed_by)
                self._posted.discard(affected)
            return CorrectResponse(correction_id=correction.id, reran=reran)

    def explain(self, txn_id: str) -> ExplainResponse:
        decision = self.decision(txn_id)
        return ExplainResponse(transaction_id=txn_id, explanation=_narrate(decision))

    def metrics(self) -> EvalReport:
        return run_eval(list(self._decisions.values()), self._repo)

    def trace(self, txn_id: str) -> Trace:
        decision = self.decision(txn_id)
        txn = self._transaction(txn_id)
        claimed_by = self._resolved_claims(exclude=txn_id)
        evidence = build_evidence(txn, self._repo, self._customer, claimed_by)
        proposal = _proposal_from_decision(decision)
        verdict = run_guard(proposal, txn, self._repo, claimed_by)
        return Trace(
            transaction_id=txn_id,
            context=_context(evidence),
            prompt=render_prompt(evidence),
            llm_output=proposal,
            verification=verdict.model_dump(mode="json"),
            confidence_signals=list(decision.confidence_signals),
            decision=decision,
        )

    def _resolved_claims(self, exclude: str | None = None) -> dict[str, list[str]]:
        """The resolved-settlement collision map from the run's decisions, dropping ``exclude``'s own.

        Holds what earlier decisions actually settled (each Decision's match), so re-running or tracing
        a transaction is guarded against other decisions' resolved matches, never its own stale prior.
        """
        claimed: dict[str, list[str]] = {}
        for decision in self._decisions.values():
            if decision.transaction_id == exclude:
                continue
            for doc_id in decision.match:
                claimed.setdefault(doc_id, []).append(decision.transaction_id)
        return claimed

    def _find(self, txn_id: str) -> Transaction | None:
        for txn in self._repo.transactions(self._customer):
            if txn.id == txn_id:
                return txn
        return None

    def _transaction(self, txn_id: str) -> Transaction:
        txn = self._find(txn_id)
        if txn is None:
            raise HTTPException(status_code=404, detail=f"transaction {txn_id} not found")
        return txn


app = FastAPI(title="Project AGL", description="Accountant-supervised categorization and reconciliation.")
_console = Console.create()


@app.post("/run")
async def run() -> list[Decision]:
    """Run the engine over the customer's transactions and return every Decision."""
    return await _console.run()


@app.get("/queue")
async def queue() -> list[Decision]:
    """Return the review queue: the deferred decisions ranked by where the accountant's attention is worth most."""
    return _console.queue()


@app.get("/posted")
async def posted() -> list[Decision]:
    """Return the posted ledger: auto-posted decisions plus any the accountant accepted, spot-checkable without re-running."""
    return _console.posted()


@app.get("/transaction/{transaction_id}")
async def get_transaction(transaction_id: str) -> Decision:
    """Return the Decision card for one transaction."""
    return _console.decision(transaction_id)


@app.post("/transaction/{transaction_id}/accept")
async def accept_transaction(transaction_id: str) -> Decision:
    """Accept (post) the agent's decision for one transaction."""
    return _console.accept(transaction_id)


@app.post("/transaction/{transaction_id}/correct")
async def correct_transaction(transaction_id: str, body: CorrectRequest) -> CorrectResponse:
    """Apply the accountant's correction and re-run the pending similar transactions."""
    return await _console.correct(transaction_id, body.corrected_account, body.corrected_match)


@app.post("/transaction/{transaction_id}/explain")
async def explain_transaction(transaction_id: str) -> ExplainResponse:
    """On-demand explanation: narrates the agent's decision for one transaction."""
    return _console.explain(transaction_id)


@app.get("/metrics")
async def metrics() -> EvalReport:
    """Return the eval report: accuracy, false-confidence, routing counts, and per-outcome gates.

    The cold-vs-warm learning lift is produced by ``scripts/run_eval.py``, not this endpoint.
    """
    return _console.metrics()


@app.get("/trace/{transaction_id}")
async def get_trace(transaction_id: str) -> Trace:
    """Return the full per-transaction trace: context, prompt, raw output, verification, confidence, decision."""
    return _console.trace(transaction_id)


_UI_DIR = Path(__file__).resolve().parent.parent / "ui"
app.mount("/", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")

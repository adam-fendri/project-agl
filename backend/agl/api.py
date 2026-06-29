from __future__ import annotations

import asyncio
import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agl.agent import ClaudeCliAgent, LlmAgent
from agl.engine import decide, finalize, run_batch
from agl.eval import EvalReport, run_eval
from agl.grounding import build_evidence, render_prompt
from agl.guard import run_guard
from agl.learning import apply_correction, pending_reruns
from agl.models import (
    Account,
    AgentProtocol,
    Confidence,
    Customer,
    Decision,
    DocumentStatus,
    Evidence,
    Outcome,
    Proposal,
    Rubriek,
    Trace,
    Transaction,
)
from agl.observability import configure_logfire
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

_HANDLE_ACTION: dict[Outcome, str] = {
    Outcome.ANOMALY: "flag_duplicate",
    Outcome.REQUEST_DOCUMENT: "request_document",
}


class CorrectRequest(BaseModel):
    corrected_account: str | None = None
    corrected_match: list[str] | None = None


class CorrectResponse(BaseModel):
    correction_id: str
    reran: list[str]


class CreateAccountRequest(BaseModel):
    number: str
    name_en: str
    name_nl: str
    rubriek: Rubriek


class AssignAccountRequest(BaseModel):
    number: str
    name_en: str | None = None
    name_nl: str | None = None
    rubriek: Rubriek | None = None


class ExplainResponse(BaseModel):
    transaction_id: str
    explanation: str


class HandledRecord(BaseModel):
    """What the accountant did with a flagged decision: the next action, logged out of the active queue."""

    transaction_id: str
    action: str
    vendor: str
    account: str


class DocumentView(BaseModel):
    """An invoice or bill flattened for the console: the fields an accountant needs to read a match or re-point one."""

    id: str
    kind: str
    party: str
    net: Decimal
    vat: Decimal
    gross: Decimal
    date: date
    status: DocumentStatus
    account: str | None = None


def _documents(repo: Repository, customer_id: str) -> list[DocumentView]:
    views = [
        DocumentView(
            id=inv.id,
            kind="invoice",
            party=inv.client,
            net=inv.net,
            vat=inv.vat,
            gross=inv.gross,
            date=inv.issued_on,
            status=inv.status,
        )
        for inv in repo.invoices(customer_id)
    ]
    views += [
        DocumentView(
            id=bill.id,
            kind="bill",
            party=bill.supplier,
            net=bill.net,
            vat=bill.vat,
            gross=bill.gross,
            date=bill.received_on,
            status=bill.status,
            account=bill.account,
        )
        for bill in repo.bills(customer_id)
    ]
    return views


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
        self._handled: dict[str, HandledRecord] = {}
        self._lock = asyncio.Lock()
        self._state_file = repo.runtime_dir / "console_state.json"
        self._load_state()

    @classmethod
    def create(cls) -> Console:
        return cls(Repository(), _select_agent(), os.getenv("AGL_CUSTOMER", _DEFAULT_CUSTOMER))

    async def run(self) -> list[Decision]:
        async with self._lock:
            decisions = await run_batch(self._repo, self._agent, self._customer)
            self._decisions = {decision.transaction_id: decision for decision in decisions}
            self._save_state()
            return decisions

    def queue(self) -> list[Decision]:
        deferred = [
            decision
            for decision in self._decisions.values()
            if decision.outcome is not Outcome.AUTO_POST
            and decision.transaction_id not in self._posted
            and decision.transaction_id not in self._handled
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
        self._save_state()
        return found

    def posted(self) -> list[Decision]:
        return [
            decision
            for decision in self._decisions.values()
            if decision.outcome is Outcome.AUTO_POST or decision.transaction_id in self._posted
        ]

    def handle(self, txn_id: str) -> HandledRecord:
        decision = self.decision(txn_id)
        action = _HANDLE_ACTION.get(decision.outcome)
        if action is None:
            raise HTTPException(
                status_code=409,
                detail=f"{txn_id} is {decision.outcome.value}; post it via /accept, not /handle",
            )
        record = HandledRecord(
            transaction_id=txn_id, action=action, vendor=decision.vendor, account=decision.account
        )
        self._handled[txn_id] = record
        self._save_state()
        return record

    def handled(self) -> list[HandledRecord]:
        return list(self._handled.values())

    def _save_state(self) -> None:
        self._repo.runtime_dir.mkdir(parents=True, exist_ok=True)
        state = {
            "customer": self._customer,
            "decisions": [d.model_dump(mode="json") for d in self._decisions.values()],
            "posted": sorted(self._posted),
            "handled": [h.model_dump(mode="json") for h in self._handled.values()],
        }
        self._state_file.write_text(json.dumps(state, indent=2))

    def _load_state(self) -> None:
        if not self._state_file.exists():
            return
        try:
            state = json.loads(self._state_file.read_text())
            if state.get("customer") != self._customer:
                return
            self._decisions = {
                d["transaction_id"]: Decision.model_validate(d) for d in state.get("decisions", [])
            }
            self._posted = set(state.get("posted", []))
            self._handled = {
                h["transaction_id"]: HandledRecord.model_validate(h) for h in state.get("handled", [])
            }
        except (json.JSONDecodeError, KeyError, ValueError):
            return

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
                settled_by = self._resolved_claims(exclude=affected)
                evidence, proposal = await decide(txn, self._repo, self._agent)
                self._decisions[affected] = finalize(
                    txn, self._repo, evidence, proposal, settled_by
                )
                self._posted.discard(affected)
            self._save_state()
            return CorrectResponse(correction_id=correction.id, reran=reran)

    async def create_account(self, body: CreateAccountRequest) -> Account:
        async with self._lock:
            account = self._account(body.number, body.name_en, body.name_nl, body.rubriek)
            try:
                self._repo = self._repo.add_account(account)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e)) from e
            return account

    async def assign_account(self, txn_id: str, body: AssignAccountRequest) -> list[Decision]:
        async with self._lock:
            decision = self.decision(txn_id)
            if body.number not in {a.number for a in self._repo.accounts(self._customer)}:
                try:
                    self._repo = self._repo.add_account(self._new_account(body))
                except ValueError as e:
                    raise HTTPException(status_code=422, detail=str(e)) from e
            try:
                correction = apply_correction(
                    self._repo, txn_id, body.number, None, vendor=decision.vendor
                )
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e)) from e
            self._repo = self._repo.reload()
            reran = pending_reruns(correction, list(self._decisions.values()))
            updated: list[Decision] = []
            for affected in [txn_id, *reran]:
                txn = self._find(affected)
                if txn is None:
                    continue
                settled_by = self._resolved_claims(exclude=affected)
                evidence, proposal = await decide(txn, self._repo, self._agent)
                self._decisions[affected] = finalize(txn, self._repo, evidence, proposal, settled_by)
                self._posted.discard(affected)
                updated.append(self._decisions[affected])
            self._save_state()
            return updated

    def _account(self, number: str, name_en: str, name_nl: str, rubriek: Rubriek) -> Account:
        balance_sheet = (Rubriek.FIXED_ASSETS_EQUITY, Rubriek.FINANCIAL, Rubriek.FINANCIAL_RESULT)
        return Account(
            number=number,
            customer_id=self._customer,
            name_nl=name_nl,
            name_en=name_en,
            rubriek=rubriek,
            rgs_group="",
            vat_treatment="exempt" if rubriek in balance_sheet else "standard",
        )

    def _new_account(self, body: AssignAccountRequest) -> Account:
        if body.name_en is None or body.name_nl is None or body.rubriek is None:
            raise HTTPException(
                status_code=422,
                detail=f"account {body.number!r} is not in the chart; provide name_en, name_nl, and rubriek to create it",
            )
        return self._account(body.number, body.name_en, body.name_nl, body.rubriek)

    def explain(self, txn_id: str) -> ExplainResponse:
        decision = self.decision(txn_id)
        return ExplainResponse(transaction_id=txn_id, explanation=_narrate(decision))

    def metrics(self) -> EvalReport:
        return run_eval(list(self._decisions.values()), self._repo)

    def customer(self) -> Customer:
        found = self._repo.customer(self._customer)
        if found is None:
            raise HTTPException(status_code=404, detail=f"customer {self._customer!r} not found")
        return found

    def accounts(self) -> list[Account]:
        return self._repo.accounts(self._customer)

    def documents(self) -> list[DocumentView]:
        return _documents(self._repo, self._customer)

    def transactions(self) -> list[Transaction]:
        return self._repo.transactions(self._customer)

    def trace(self, txn_id: str) -> Trace:
        decision = self.decision(txn_id)
        txn = self._transaction(txn_id)
        settled_by = self._resolved_claims(exclude=txn_id)
        evidence = build_evidence(txn, self._repo, self._customer)
        proposal = _proposal_from_decision(decision)
        verdict = run_guard(proposal, txn, self._repo, settled_by)
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
        """The full resolved-settlement map (doc id -> transaction ids) over every current decision,
        dropping ``exclude``'s own match.

        Used as ``settled_by`` so re-running or tracing a transaction is guarded against the full set of
        the other decisions' resolved matches, never its own stale prior. Order-independent: a duplicate
        is the later claimant of a shared document.
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


configure_logfire()
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


@app.get("/handled")
async def handled() -> list[HandledRecord]:
    """Return the handled ledger: anomalies flagged and held, and document requests logged, out of the active queue."""
    return _console.handled()


@app.get("/customer")
async def customer() -> Customer:
    """Return the client whose books the accountant is working: name, VAT scheme, period, owner."""
    return _console.customer()


@app.get("/accounts")
async def accounts() -> list[Account]:
    """Return the customer's chart of accounts (number, names, rubriek, VAT treatment) for the correction picker."""
    return _console.accounts()


@app.get("/documents")
async def documents() -> list[DocumentView]:
    """Return the customer's invoices and bills (party, amount, date, paid/unpaid) for reading and re-pointing a match."""
    return _console.documents()


@app.get("/transactions")
async def transactions() -> list[Transaction]:
    """Return the raw transactions so the console renders each card in human terms (date, party, amount, description)."""
    return _console.transactions()


@app.get("/transaction/{transaction_id}")
async def get_transaction(transaction_id: str) -> Decision:
    """Return the Decision card for one transaction."""
    return _console.decision(transaction_id)


@app.post("/transaction/{transaction_id}/accept")
async def accept_transaction(transaction_id: str) -> Decision:
    """Accept (post) the agent's decision for one transaction."""
    return _console.accept(transaction_id)


@app.post("/transaction/{transaction_id}/handle")
async def handle_transaction(transaction_id: str) -> HandledRecord:
    """Record the accountant's next action on a flagged (anomaly / request-document) decision."""
    return _console.handle(transaction_id)


@app.post("/transaction/{transaction_id}/correct")
async def correct_transaction(transaction_id: str, body: CorrectRequest) -> CorrectResponse:
    """Apply the accountant's correction and re-run the pending similar transactions."""
    return await _console.correct(transaction_id, body.corrected_account, body.corrected_match)


@app.post("/account")
async def create_account(body: CreateAccountRequest) -> Account:
    """Create a new chart-of-accounts entry for the customer and return it; the chart grows at runtime."""
    return await _console.create_account(body)


@app.post("/transaction/{transaction_id}/assign-account")
async def assign_account(transaction_id: str, body: AssignAccountRequest) -> list[Decision]:
    """Create the account if new, assign the transaction to it so the cohort learns it, and re-run the affected and sibling decisions."""
    return await _console.assign_account(transaction_id, body)


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


_UI_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
app.mount("/", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")

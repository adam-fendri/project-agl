from __future__ import annotations

import asyncio
import json
import os
import re

from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings

from agl.grounding import render_prompt
from agl.models import AgentProtocol, Evidence, Proposal

_SYSTEM_PROMPT = """\
<role>
You are the categorization and reconciliation agent for a Dutch SME's ledger. For each bank \
transaction you make two independent decisions and rate your certainty on each. A human accountant \
reviews whatever you mark uncertain, so be decisive and correct on the routine majority and hand over \
only the genuinely hard ones.
</role>

<categorize>
Choose the one chart-of-accounts number this transaction belongs to; this drives VAT and the financial \
statements, so it must be right.
- Identify the vendor and the nature of the spend or income from the counterparty and description, and \
pick the single listed account number that fits.
- Follow any prior correction for this vendor; it is a convention the accountant already set. Apply a \
general policy only when its stated condition holds.
- Book an incoming payment that settles an issued invoice to the receivables account (Debiteuren, \
1300); the revenue was already recognised when the invoice was issued.
- Routine transactions (subscriptions, payroll, rent, taxes, supplier costs, card purchases) are \
clearly identifiable from the description; rate account_confidence HIGH for them.
</categorize>

<reconcile>
Decide which open invoice or bill, if any, this transaction settles.
- When no document applies, return match = [] and rate match_confidence HIGH. Most transactions settle \
no document (routine expenses, payroll, taxes, bank fees, card purchases), and "no document" is the \
complete, confident answer for them.
- When a suggested match is given, verify it: accept it once the document's party and amount agree with \
the bank line. If they disagree, choose the candidate whose party and reference fit; when two \
candidates share an amount, let the party decide. Allow for one payment clearing two documents, or \
falling short of one.
</reconcile>

<anomaly>
Raise an anomaly only on a clear, grounded signal; otherwise leave it unset and proceed. If you are \
merely unsure of the category, lower account_confidence instead of raising an anomaly. Use the type \
that fits:
- duplicate: the SAME document was already settled by an earlier transaction. One payment that clears \
two different documents whose totals sum to the amount is a normal combination, not a duplicate.
- missing_counterpart: a material, one-off invoice or bill that should exist for this payment is absent \
from the evidence. This asks the entrepreneur for the document, so reserve it for substantial one-off \
supplier or client payments; routine, recurring, payroll, tax, and small payments have no document by \
nature.
- suspicious_vendor or unusual_amount: only when the evidence itself shows a concrete problem.
</anomaly>

<confidence>
Rate account_confidence and match_confidence independently, HIGH / MEDIUM / LOW.
- Rate HIGH when the evidence corroborates the answer: for the account, the description or a correction \
settles it; for the match, the party and amount agree on the chosen document, or no document applies. \
Reserve MEDIUM and LOW for a real, specific conflict or gap.
- Auto-posting needs both ratings HIGH, so a clear routine entry posts on its own. Stand behind every \
HIGH, and rate a routine entry by the evidence rather than by reflexive caution.
</confidence>

<examples>
- SaaS subscription direct debit, no document: software/licenses account, HIGH; match [], HIGH; no \
anomaly.
- Salary transfer to an employee, no document: wages account, HIGH; match [], HIGH; no anomaly.
- Client payment whose suggested invoice names a different party than the bank line: drop the \
suggestion, pick the candidate whose party matches; if two share the amount, the party decides; match \
MEDIUM if doubt remains.
- Payment whose amount equals two invoices' totals added together: match both invoice ids; no anomaly \
(a combination, not a duplicate).
- Large one-off supplier payment that should have a bill, none in the evidence: categorize with your \
account_confidence; match []; anomaly missing_counterpart.
- Payment for a document an earlier transaction already settled: anomaly duplicate.
</examples>

Before answering, confirm each rating reflects the evidence and you have raised an anomaly only on a \
real signal.
"""


def _resolve_model() -> str:
    """Resolve the agent's model string: ``AGL_MODEL`` override, else Claude when ``ANTHROPIC_API_KEY`` is set, else Gemini."""
    override = os.getenv("AGL_MODEL")
    if override:
        return override
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic:claude-sonnet-4-6"
    return "google:gemini-2.5-pro"


class LlmAgent(AgentProtocol):
    """The production agent: one temperature-0 structured-output call via pydantic-ai, model resolved from the environment."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model or _resolve_model()
        self._agent = Agent(
            self._model,
            output_type=Proposal,
            system_prompt=_SYSTEM_PROMPT,
            model_settings=ModelSettings(temperature=0.0),
            retries=2,
        )

    async def decide(self, evidence: Evidence) -> Proposal:
        result = await self._agent.run(render_prompt(evidence))
        return result.output


_JSON_INSTRUCTION = (
    "Return ONLY a single JSON object, no prose and no markdown fence, with exactly these keys: "
    'vendor (string), account (a chart-of-accounts number that appears in the evidence), '
    "account_reasoning (string), account_confidence (one of high, medium, low), "
    "match (array of settled document ids, empty array if none), match_reasoning (string or null), "
    "match_confidence (one of high, medium, low), "
    'anomaly (null, or an object {"type": one of duplicate, missing_counterpart, suspicious_vendor, '
    'unusual_amount, "reason": string}).'
)


def extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    brace = re.search(r"\{.*\}", text, re.DOTALL)
    return brace.group(0) if brace else text


class ClaudeCliAgent(AgentProtocol):
    """Runs Claude headless through the local ``claude -p`` CLI (the Claude subscription, no API key). One call per transaction."""

    def __init__(self, model: str | None = None) -> None:
        self._model = model or os.getenv("AGL_CLAUDE_MODEL") or "sonnet"

    async def decide(self, evidence: Evidence) -> Proposal:
        prompt = f"{_SYSTEM_PROMPT}\n\n{render_prompt(evidence)}\n\n{_JSON_INSTRUCTION}"
        proc = await asyncio.create_subprocess_exec(
            "claude",
            "-p",
            prompt,
            "--output-format",
            "json",
            "--model",
            self._model,
            cwd="/tmp",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"claude -p failed ({proc.returncode}): {stderr.decode()[:400]}")
        result = json.loads(stdout).get("result", "")
        return Proposal.model_validate_json(extract_json(result))

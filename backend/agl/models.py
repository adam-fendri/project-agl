from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Protocol

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from agl.reconcile import Candidate


class Rubriek(str, Enum):
    FIXED_ASSETS_EQUITY = "0"
    FINANCIAL = "1"
    COSTS = "4"
    REVENUE = "8"
    FINANCIAL_RESULT = "9"


class TransactionType(str, Enum):
    SEPA_TRANSFER = "sepa_transfer"
    SEPA_DIRECT_DEBIT = "sepa_direct_debit"
    IDEAL = "ideal"
    CARD = "card"
    OTHER = "other"


class DocumentStatus(str, Enum):
    UNPAID = "unpaid"
    PAID = "paid"


class AnomalyType(str, Enum):
    DUPLICATE = "duplicate"
    MISSING_COUNTERPART = "missing_counterpart"
    SUSPICIOUS_VENDOR = "suspicious_vendor"
    UNUSUAL_AMOUNT = "unusual_amount"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class MatchStatus(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    NONE = "none"


class Outcome(str, Enum):
    AUTO_POST = "auto_post"
    REVIEW = "review"
    ANOMALY = "anomaly"
    REQUEST_DOCUMENT = "request_document"


class Account(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    number: str
    customer_id: str
    name_nl: str
    name_en: str
    rubriek: Rubriek
    rgs_group: str
    vat_treatment: str


class Transaction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    customer_id: str
    booked_on: date
    amount: Decimal
    counterparty: str
    description: str
    type: TransactionType


class Invoice(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    customer_id: str
    client: str
    issued_on: date
    net: Decimal
    vat: Decimal
    gross: Decimal
    status: DocumentStatus


class Bill(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    customer_id: str
    supplier: str
    received_on: date
    net: Decimal
    vat: Decimal
    gross: Decimal
    account: str
    status: DocumentStatus


class ProvidedMatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    transaction_id: str
    document_id: str
    source: str = "neno_infra"


class Correction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    customer_id: str
    transaction_id: str | None = None
    vendor: str
    corrected_account: str | None = None
    corrected_match: str | None = None
    note: str = ""
    created_at: datetime


class Anomaly(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: AnomalyType
    reason: str


class Proposal(BaseModel):
    """The LLM's structured output for one transaction. Field descriptions are the model's instructions."""

    model_config = ConfigDict(extra="forbid")

    vendor: str = Field(description="The canonical merchant/vendor identified from the messy bank line.")
    account: str = Field(description="The chart-of-accounts number this transaction most likely belongs to.")
    account_reasoning: str = Field(description="One short sentence: why this account, from the description.")
    account_confidence: Confidence = Field(
        description="How sure the account is right: high only when the description plus any correction make it unambiguous."
    )
    account_unlisted: bool = Field(
        default=False,
        description="True only when no listed account properly fits the spend, the general other-costs line included.",
    )
    match: list[str] = Field(
        default_factory=list,
        description="The invoice/bill id(s) this transaction settles — usually one, two when one payment clears two documents, empty if none.",
    )
    match_reasoning: str | None = Field(
        default=None, description="One short sentence: why this document (or these documents), or null."
    )
    match_confidence: Confidence = Field(
        description="How sure the match is right: high only when both the counterparty/reference and the amount corroborate."
    )
    anomaly: Anomaly | None = Field(
        default=None, description="Set only if something looks wrong (fraud, miscategorized, missing counterpart)."
    )


@dataclass(frozen=True)
class CandidateFact:
    """A reconciliation candidate paired with its resolved documents (which carry their own paid/unpaid status)."""

    candidate: Candidate
    documents: list[Invoice | Bill]


@dataclass(frozen=True)
class VendorHistoryEntry:
    """A prior transaction for the same vendor and the account it was booked to."""

    transaction_id: str
    counterparty: str
    account: str
    amount: Decimal
    booked_on: date


@dataclass(frozen=True)
class Evidence:
    """The grounded per-transaction context the agent reads to decide: facts in, no guesses."""

    transaction: Transaction
    accounts: list[Account]
    provided_match: CandidateFact | None
    candidates: list[CandidateFact]
    corrections: list[Correction]
    vendor_history: list[VendorHistoryEntry]
    referenced_documents: list[str] = field(default_factory=list[str])


class GuardVerdict(BaseModel):
    """The strict backstop's result: it may only DOWNGRADE an auto-post to review, never rewrite the agent's choice."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    failed_checks: list[str] = Field(default_factory=list)
    forced_outcome: Outcome | None = None


class Decision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    transaction_id: str
    vendor: str
    account: str
    account_reasoning: str
    account_confidence: Confidence
    account_unlisted: bool = False
    vat_treatment: str = ""
    match: list[str]
    match_reasoning: str | None
    match_status: MatchStatus
    match_confidence: Confidence
    anomaly: Anomaly | None
    confidence_signals: list[str]
    outcome: Outcome
    sources: list[str]


class GroundTruth(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    transaction_id: str
    account: str
    match: list[str]
    outcome: Outcome


class Trace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: str
    context: dict[str, object]
    prompt: str
    llm_output: Proposal | None
    verification: dict[str, object]
    confidence_signals: list[str]
    decision: Decision


class AgentProtocol(Protocol):
    """The agent (LLM) decides; code only grounds and guards. One structured-output call per transaction."""

    async def decide(self, evidence: Evidence) -> Proposal: ...

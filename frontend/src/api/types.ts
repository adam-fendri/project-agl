export type Confidence = "high" | "medium" | "low";
export type Outcome = "auto_post" | "review" | "anomaly" | "request_document";
export type MatchStatus = "full" | "partial" | "none";
export type Rubriek = "0" | "1" | "4" | "8" | "9";
export type DocumentStatus = "unpaid" | "paid";
export type DocumentKind = "invoice" | "bill";
export type TransactionType =
  | "sepa_transfer"
  | "sepa_direct_debit"
  | "ideal"
  | "card"
  | "other";
export type AnomalyType =
  | "duplicate"
  | "missing_counterpart"
  | "suspicious_vendor"
  | "unusual_amount";

export interface Customer {
  id: string;
  name: string;
  legal_form: string;
  city: string;
  country: string;
  industry: string;
  headcount: number;
  vat_rate: string;
  vat_filing: string;
  fiscal_period: string;
  owner: string;
  kvk: string;
}

export interface Account {
  number: string;
  customer_id: string;
  name_nl: string;
  name_en: string;
  rubriek: Rubriek;
  rgs_group: string;
  vat_treatment: string;
}

export interface DocumentView {
  id: string;
  kind: DocumentKind;
  party: string;
  net: string;
  vat: string;
  gross: string;
  date: string;
  status: DocumentStatus;
  account: string | null;
}

export interface Transaction {
  id: string;
  customer_id: string;
  booked_on: string;
  amount: string;
  counterparty: string;
  description: string;
  type: TransactionType;
}

export interface Anomaly {
  type: AnomalyType;
  reason: string;
}

export interface Decision {
  transaction_id: string;
  vendor: string;
  account: string;
  account_reasoning: string;
  account_confidence: Confidence;
  account_unlisted: boolean;
  vat_treatment: string;
  match: string[];
  match_reasoning: string | null;
  match_status: MatchStatus;
  match_confidence: Confidence;
  anomaly: Anomaly | null;
  confidence_signals: string[];
  outcome: Outcome;
  sources: string[];
}

export interface HandledRecord {
  transaction_id: string;
  action: string;
  vendor: string;
  account: string;
}

export interface MetricCounts {
  total: number;
  auto_post: number;
  review: number;
  anomaly: number;
  request_document: number;
  categorization_correct: number;
  match_correct: number;
  reconciliation_total: number;
  reconciliation_correct: number;
  anomalies_expected: number;
  anomalies_caught: number;
  anomaly_false_positives: number;
}

export interface EvalReport {
  categorization_accuracy: number;
  match_accuracy: number;
  reconciliation_accuracy: number;
  false_confidence_count: number;
  false_confidence_categorization: number;
  false_confidence_reconciliation: number;
  counts: MetricCounts;
}

export interface Proposal {
  vendor: string;
  account: string;
  account_reasoning: string;
  account_confidence: Confidence;
  account_unlisted: boolean;
  match: string[];
  match_reasoning: string | null;
  match_confidence: Confidence;
  anomaly: Anomaly | null;
}

export interface Trace {
  transaction_id: string;
  context: Record<string, unknown>;
  prompt: string;
  llm_output: Proposal | null;
  verification: Record<string, unknown>;
  confidence_signals: string[];
  decision: Decision;
}

export interface CorrectResponse {
  correction_id: string;
  reran: string[];
}

export interface CorrectRequest {
  corrected_account?: string;
  corrected_match?: string[];
}

export interface AssignAccountRequest {
  number: string;
  name_en?: string;
  name_nl?: string;
  rubriek?: Rubriek;
}

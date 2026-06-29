import type {
  AnomalyType,
  Confidence,
  Outcome,
  Rubriek,
  TransactionType,
} from "../api/types";

export type Tone = "success" | "warning" | "danger" | "info" | "neutral";

export const RUBRIEK_LABEL: Record<Rubriek, string> = {
  "0": "Fixed assets & equity",
  "1": "Financial",
  "4": "Costs",
  "8": "Revenue",
  "9": "Financial result",
};

export const RUBRIEK_ORDER: Rubriek[] = ["0", "1", "4", "8", "9"];

export const OUTCOME_LABEL: Record<Outcome, string> = {
  auto_post: "Auto-posted",
  review: "Needs review",
  anomaly: "Anomaly",
  request_document: "Document request",
};

export const OUTCOME_TONE: Record<Outcome, Tone> = {
  auto_post: "success",
  review: "warning",
  anomaly: "danger",
  request_document: "info",
};

export const CONFIDENCE_LABEL: Record<Confidence, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

export const CONFIDENCE_TONE: Record<Confidence, Tone> = {
  high: "success",
  medium: "warning",
  low: "danger",
};

export const TXN_TYPE_LABEL: Record<TransactionType, string> = {
  sepa_transfer: "SEPA transfer",
  sepa_direct_debit: "SEPA direct debit",
  ideal: "iDEAL",
  card: "Card payment",
  other: "Other",
};

export const ANOMALY_LABEL: Record<AnomalyType, string> = {
  duplicate: "Possible duplicate",
  missing_counterpart: "Missing document",
  suspicious_vendor: "Suspicious vendor",
  unusual_amount: "Unusual amount",
};

export const ANOMALY_NEXT: Record<AnomalyType, string> = {
  duplicate:
    "Confirm this is a duplicate and hold it. Check with the entrepreneur before anything posts.",
  missing_counterpart:
    "Request the missing invoice or bill from the entrepreneur so the payment can be matched.",
  suspicious_vendor:
    "Escalate. Verify the vendor's identity and bank details before posting.",
  unusual_amount:
    "Confirm the amount with the entrepreneur. It sits outside this vendor's normal range.",
};

export const ANOMALY_ACTION: Record<AnomalyType, string> = {
  duplicate: "Confirm duplicate",
  missing_counterpart: "Request the missing document",
  suspicious_vendor: "Escalate vendor",
  unusual_amount: "Confirm amount",
};

export const HANDLED_LABEL: Record<string, string> = {
  flag_duplicate: "Flagged & held",
  request_document: "Document requested",
};

export const HANDLED_TONE: Record<string, Tone> = {
  flag_duplicate: "danger",
  request_document: "info",
};

export function vatLabel(treatment: string): string {
  switch (treatment) {
    case "standard":
      return "21% — standard-rated";
    case "reduced":
      return "9% — reduced rate";
    case "exempt":
      return "Exempt / 0%";
    case "":
      return "Not applicable";
    default:
      return treatment
        .split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(" ");
  }
}

export function requestDocumentNext(): string {
  return "Request the matching invoice or bill from the entrepreneur, then re-run this transaction.";
}

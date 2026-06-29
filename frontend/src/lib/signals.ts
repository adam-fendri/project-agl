const STATIC_SIGNALS: Record<string, string> = {
  account_in_chart:
    "The chosen account already exists in this client's chart of accounts.",
  account_verified:
    "The account is corroborated — a prior booking, a correction, or the VAT rate matches.",
  account_unverified:
    "The account is the agent's best read but is not independently corroborated by a prior booking or correction.",
  account_unlisted:
    "No existing account fits this spend — the accountant should add one.",
  provided_match_confirmed:
    "The provided match was confirmed — the party and the amount agree.",
  provided_match_overridden:
    "The provided match was overridden after verification.",
  amount_sums_exactly: "The amount matches the document exactly.",
  amount_not_exact:
    "The amount does not match exactly — this may be a partial payment.",
  no_match: "No open invoice or bill corresponds to this payment.",
};

function sentence(value: string): string {
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return "A grounded check was recorded.";
  }
  const text = trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
  return text.endsWith(".") ? text : `${text}.`;
}

function humanizeToken(token: string): string {
  return sentence(token.replace(/^guard:/, "").replace(/[:_]+/g, " "));
}

export function humanizeSignal(token: string): string {
  const known = STATIC_SIGNALS[token];
  if (known) {
    return known;
  }
  if (token.startsWith("guard:duplicate:")) {
    return `Document ${token.slice("guard:duplicate:".length)} was already settled by another transaction — likely a duplicate.`;
  }
  if (token.startsWith("guard:possible_duplicate_payment:")) {
    return `A near-identical payment already exists (${token.slice("guard:possible_duplicate_payment:".length)}).`;
  }
  if (token.startsWith("guard:amount_mismatch")) {
    return "The paid amount does not match the document total.";
  }
  if (token === "guard:missing_document" || token.startsWith("guard:missing_document")) {
    return "A material supporting document is missing for this payment.";
  }
  if (token.startsWith("guard:")) {
    return humanizeToken(token);
  }
  return humanizeToken(token);
}

export function humanizeSignals(tokens: string[]): string[] {
  return tokens.map(humanizeSignal);
}

export function humanizeGuardCheck(check: string): string {
  if (check.startsWith("duplicate:")) {
    return `${check.slice("duplicate:".length)} was already settled by another transaction — a duplicate.`;
  }
  if (check.startsWith("possible_duplicate_payment:")) {
    return `A near-identical payment exists (${check.slice("possible_duplicate_payment:".length)}).`;
  }
  if (check.startsWith("amount_mismatch")) {
    return "The paid amount does not match the document total.";
  }
  if (check.startsWith("missing_document")) {
    return "A material supporting document is missing.";
  }
  return sentence(check.replace(/[:_]+/g, " "));
}

const GOOD_SIGNALS = new Set([
  "account_verified",
  "account_in_chart",
  "amount_sums_exactly",
  "provided_match_confirmed",
]);

export function signalTone(token: string): "success" | "warning" | "danger" {
  if (token.startsWith("guard:")) {
    return "danger";
  }
  if (GOOD_SIGNALS.has(token)) {
    return "success";
  }
  return "warning";
}

export type SourceKind = "document" | "account" | "correction" | "other";

export interface ParsedSource {
  kind: SourceKind;
  id: string;
}

export function parseSource(token: string): ParsedSource {
  const [prefix, ...rest] = token.split(":");
  const id = rest.join(":");
  if ((prefix === "document" || prefix === "account" || prefix === "correction") && id) {
    return { kind: prefix, id };
  }
  return { kind: "other", id: token };
}

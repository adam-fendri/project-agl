const DOCUMENT_RE = /\b(?:INV-\d{4}-\d{2,}|B-\d{2,})\b/i;
const IBAN_TOKEN = /^[A-Z]{2}\d{2}[A-Z0-9]{8,30}$/;
const IBAN_GLOBAL = /\b[A-Z]{2}\d{2}[A-Z0-9]{8,30}\b/g;

export function looksLikeIban(value: string): boolean {
  return IBAN_TOKEN.test(value.replace(/\s+/g, "").toUpperCase());
}

export interface Reference {
  label: string;
  value: string;
  documentId: string | null;
}

export function extractReference(description: string): Reference | null {
  const doc = description.match(DOCUMENT_RE);
  if (doc) {
    const value = doc[0].toUpperCase();
    return { label: "Invoice reference", value, documentId: value };
  }
  const remi = description.match(/REMI\/[^/]*\/([^/\s]+)/i);
  if (remi) {
    return { label: "Remittance reference", value: remi[1], documentId: null };
  }
  const ref = description.match(/\bREF\s+([A-Z0-9][A-Z0-9-]{2,})/i);
  if (ref) {
    return { label: "Payment reference", value: ref[1], documentId: null };
  }
  const kenmerk = description.match(/\bKENMERK\s+([A-Z0-9][A-Z0-9-]{2,})/i);
  if (kenmerk) {
    return { label: "Reference", value: kenmerk[1], documentId: null };
  }
  const mandate = description.match(/\bMANDAAT\s+([A-Z0-9][A-Z0-9-]{2,})/i);
  if (mandate) {
    return { label: "SEPA mandate", value: mandate[1], documentId: null };
  }
  return null;
}

export function extractCounterpartyName(description: string): string | null {
  const named = description.match(/\/NAME\/([^/]+)/i);
  if (named) {
    return titleCase(named[1].trim());
  }
  return null;
}

const NOISE_PATTERNS: RegExp[] = [
  /\/TRTP\/[^/]*/gi,
  /\/IBAN\/[^/]*/gi,
  /\/BIC\/[^/]*/gi,
  /\/NAME\//gi,
  /\/EREF\/[^/]*/gi,
  /\/REMI\//gi,
  /\bSEPA\b/gi,
  /\bINCASSO\b/gi,
  /\bOVERBOEKING\b/gi,
  /\bOVB\b/gi,
  /\bDD\b/gi,
  /\bIDEAL\b/gi,
  /\bBEA\b/gi,
  /\bBETAALPAS\b/gi,
  /\bPAS\d+\b/gi,
  /\bNR:[A-Z0-9]+\b/gi,
  /\bMANDAAT\s+[A-Z0-9]+/gi,
  /\bINCASSANT\s+[A-Z0-9]+/gi,
  /\bKENMERK\s+[A-Z0-9]+/gi,
  /\bKENMERK\b/gi,
  /\bREF\s+[A-Z0-9-]+/gi,
  /\bCRED\b/gi,
];

export function cleanPurpose(description: string): string | null {
  let text = description.replace(IBAN_GLOBAL, " ");
  for (const pattern of NOISE_PATTERNS) {
    text = text.replace(pattern, " ");
  }
  text = text
    .replace(/[*]/g, " ")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+\/\s+/g, " ")
    .trim();
  if (text.length < 3) {
    return null;
  }
  return titleCase(text);
}

export function titleCase(value: string): string {
  return value
    .toLowerCase()
    .split(/\s+/)
    .map((word) => {
      if (word.length === 0) {
        return word;
      }
      if (/\d/.test(word)) {
        return word.toUpperCase();
      }
      return word[0].toUpperCase() + word.slice(1);
    })
    .join(" ");
}

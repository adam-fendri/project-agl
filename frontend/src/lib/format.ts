const euro = new Intl.NumberFormat("nl-NL", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export type Direction = "in" | "out" | "flat";

export interface SignedAmount {
  direction: Direction;
  abs: number;
  display: string;
}

function toNumber(raw: string | number): number {
  const value = typeof raw === "number" ? raw : Number(raw);
  return Number.isFinite(value) ? value : 0;
}

export function formatEuro(raw: string | number): string {
  return euro.format(Math.abs(toNumber(raw)));
}

export function signedAmount(raw: string | number): SignedAmount {
  const value = toNumber(raw);
  const direction: Direction = value > 0 ? "in" : value < 0 ? "out" : "flat";
  return { direction, abs: Math.abs(value), display: euro.format(Math.abs(value)) };
}

export function formatDate(iso: string): string {
  const parts = iso.split("-").map(Number);
  const [year, month, day] = parts;
  if (!year || !month || !day) {
    return iso;
  }
  const date = new Date(year, month - 1, day);
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

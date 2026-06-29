import type { ReactNode } from "react";
import type { Confidence, Outcome } from "../../api/types";
import {
  CONFIDENCE_LABEL,
  CONFIDENCE_TONE,
  OUTCOME_LABEL,
  OUTCOME_TONE,
  type Tone,
} from "../../lib/labels";

interface PillProps {
  tone: Tone;
  children: ReactNode;
  soft?: boolean;
  title?: string;
}

export function Pill({ tone, children, soft = true, title }: PillProps) {
  return (
    <span className={`pill pill--${tone} ${soft ? "pill--soft" : "pill--solid"}`} title={title}>
      {children}
    </span>
  );
}

export function ConfidencePill({
  label,
  confidence,
}: {
  label: string;
  confidence: Confidence;
}) {
  return (
    <span className={`conf conf--${CONFIDENCE_TONE[confidence]}`}>
      <span className="conf__key">{label}</span>
      <span className="conf__dot" aria-hidden="true" />
      <span className="conf__val">{CONFIDENCE_LABEL[confidence]}</span>
    </span>
  );
}

export function OutcomePill({ outcome }: { outcome: Outcome }) {
  return (
    <Pill tone={OUTCOME_TONE[outcome]} soft>
      {OUTCOME_LABEL[outcome]}
    </Pill>
  );
}

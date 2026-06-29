import type { ReactNode } from "react";
import { useAppData } from "../data/store";
import type { Decision } from "../api/types";
import { ANOMALY_LABEL, ANOMALY_NEXT, requestDocumentNext } from "../lib/labels";
import { humanizeSignal } from "../lib/signals";
import { TransactionSummary } from "./TransactionSummary";
import { Categorization } from "./Categorization";
import { Reconciliation } from "./Reconciliation";
import { Evidence } from "./Evidence";
import { ActionBar } from "./ActionBar";
import { AuditTrail } from "./AuditTrail";
import { OutcomePill, Pill } from "./ui/Pill";
import { Spinner } from "./ui/Spinner";
import { Alert, Check, Close, FileText } from "./ui/icons";

function Notice({
  tone,
  icon,
  title,
  reason,
  next,
}: {
  tone: "danger" | "info";
  icon: ReactNode;
  title: string;
  reason: string;
  next: string;
}) {
  return (
    <div className={`anomaly anomaly--${tone}`}>
      <div className="anomaly__head">
        <span className="anomaly__icon">{icon}</span>
        <span className="anomaly__title">{title}</span>
      </div>
      <p className="anomaly__reason">{reason}</p>
      <p className="anomaly__next">
        <span className="anomaly__nextkey">Next</span>
        {next}
      </p>
    </div>
  );
}

function AnomalyNotice({ decision }: { decision: Decision }) {
  if (decision.anomaly) {
    return (
      <Notice
        tone={decision.outcome === "anomaly" ? "danger" : "info"}
        icon={<Alert size={18} />}
        title={ANOMALY_LABEL[decision.anomaly.type]}
        reason={decision.anomaly.reason}
        next={ANOMALY_NEXT[decision.anomaly.type]}
      />
    );
  }
  if (decision.outcome === "anomaly") {
    const guard = decision.confidence_signals.find(
      (token) =>
        token.startsWith("guard:duplicate:") ||
        token.startsWith("guard:possible_duplicate_payment:"),
    );
    return (
      <Notice
        tone="danger"
        icon={<Alert size={18} />}
        title="Possible duplicate payment"
        reason={guard ? humanizeSignal(guard) : "The guard held this transaction for review."}
        next={ANOMALY_NEXT.duplicate}
      />
    );
  }
  if (decision.outcome === "request_document") {
    return (
      <Notice
        tone="info"
        icon={<FileText size={18} />}
        title="Missing document"
        reason="A material supporting document is missing for this payment."
        next={requestDocumentNext()}
      />
    );
  }
  return null;
}

export function DecisionCard() {
  const { selected, selectLoading, txnById, closeDecision, isPosted, isHandled } = useAppData();

  if (selectLoading && !selected) {
    return (
      <div className="detail__loading">
        <Spinner size={26} />
      </div>
    );
  }
  if (!selected) {
    return null;
  }

  const decision = selected;
  const txn = txnById[decision.transaction_id];
  const posted = isPosted(decision.transaction_id);
  const handledFlag = isHandled(decision.transaction_id);

  return (
    <article className="card">
      <div className="card__bar">
        <div className="card__bar-left">
          <OutcomePill outcome={decision.outcome} />
          {posted && (
            <Pill tone="success" soft>
              <Check size={12} /> Posted
            </Pill>
          )}
          {handledFlag && (
            <Pill tone="neutral" soft>
              Handled
            </Pill>
          )}
        </div>
        <button type="button" className="iconbtn" onClick={closeDecision} aria-label="Close card">
          <Close size={16} />
        </button>
      </div>

      <TransactionSummary decision={decision} txn={txn} />
      <AnomalyNotice decision={decision} />

      <div className="card__grid">
        <Categorization decision={decision} />
        <Reconciliation decision={decision} />
      </div>

      <Evidence decision={decision} />
      <ActionBar decision={decision} />
      <AuditTrail decision={decision} />
    </article>
  );
}

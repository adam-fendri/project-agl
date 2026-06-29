import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAppData } from "../data/store";
import type { Decision, Outcome, Trace } from "../api/types";
import { OUTCOME_LABEL } from "../lib/labels";
import { humanizeGuardCheck, parseSource } from "../lib/signals";
import { Check, Shield } from "./ui/icons";

const OUTCOME_SENTENCE: Record<Outcome, string> = {
  auto_post: "Both confidences were high and the guard passed, so it posted automatically.",
  review: "It was deferred for the accountant to confirm before posting.",
  anomaly: "It is held in the anomaly queue until the accountant resolves it.",
  request_document: "A material document is missing, so a document request was raised.",
};

interface GuardVerdict {
  passed?: boolean;
  failed_checks?: string[];
  forced_outcome?: Outcome | null;
}

function TraceBlock({ title, text }: { title: string; text: string }) {
  return (
    <div className="traceblock">
      <h5>{title}</h5>
      <pre>{text}</pre>
    </div>
  );
}

export function AuditTrail({ decision }: { decision: Decision }) {
  const { accountByNumber, documentById } = useAppData();
  const [trace, setTrace] = useState<Trace | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    setTrace(null);
    setError(false);
    api
      .trace(decision.transaction_id)
      .then((value) => {
        if (active) {
          setTrace(value);
        }
      })
      .catch(() => {
        if (active) {
          setError(true);
        }
      });
    return () => {
      active = false;
    };
  }, [decision.transaction_id]);

  const account = accountByNumber[decision.account];
  const accountName = account ? account.name_en : "(account to be added)";
  const sources = decision.sources.map(parseSource);
  const documents = sources.filter((source) => source.kind === "document");
  const corrections = sources.filter((source) => source.kind === "correction");

  const narration = (() => {
    const parts = [
      `Booked to ${decision.account} ${accountName} with ${decision.account_confidence} account confidence.`,
    ];
    if (decision.match.length > 0) {
      parts.push(
        `Settles ${decision.match.join(", ")} — ${decision.match_status} match at ${decision.match_confidence} confidence.`,
      );
    } else {
      parts.push("No open document settles it.");
    }
    parts.push(OUTCOME_SENTENCE[decision.outcome]);
    return parts.join(" ");
  })();

  const verdict = trace ? (trace.verification as GuardVerdict) : null;

  return (
    <section className="audit">
      <div className="cardsection__head">
        <h3>Audit trail</h3>
        <span className="cardsection__sub">Everything needed to sign off</span>
      </div>

      <div className="audit__grid">
        <div className="audit__item">
          <span className="audit__k">Decision</span>
          <span className="audit__v">{narration}</span>
        </div>

        <div className="audit__item">
          <span className="audit__k">Documents read</span>
          <span className="audit__v">
            {documents.length === 0 ? (
              "No documents were required for this decision."
            ) : (
              <ul className="audit__list">
                {documents.map((source) => {
                  const document = documentById[source.id];
                  return (
                    <li key={source.id}>
                      <span className="mono">{source.id}</span>
                      {document ? ` — ${document.party}` : ""}
                    </li>
                  );
                })}
              </ul>
            )}
          </span>
        </div>

        <div className="audit__item">
          <span className="audit__k">Prior corrections applied</span>
          <span className="audit__v">
            {corrections.length === 0
              ? "None — this is a cold decision."
              : corrections.map((source) => source.id).join(", ")}
          </span>
        </div>

        <div className="audit__item">
          <span className="audit__k">
            <Shield size={14} /> Guard checks
          </span>
          <span className="audit__v">
            {error && "Guard verdict unavailable."}
            {!error && !verdict && "Loading guard checks…"}
            {verdict && verdict.passed && (
              <span className="audit__ok">
                <Check size={14} /> All guard checks passed. Nothing was overridden.
              </span>
            )}
            {verdict && !verdict.passed && (
              <>
                <ul className="audit__list audit__list--alert">
                  {(verdict.failed_checks ?? []).map((check) => (
                    <li key={check}>{humanizeGuardCheck(check)}</li>
                  ))}
                </ul>
                {verdict.forced_outcome && (
                  <span className="audit__forced">
                    The guard overrode the agent and routed this to{" "}
                    <strong>{OUTCOME_LABEL[verdict.forced_outcome]}</strong>.
                  </span>
                )}
              </>
            )}
          </span>
        </div>
      </div>

      {trace && (
        <details className="techtrace">
          <summary>Technical trace (for engineers)</summary>
          <div className="techtrace__body">
            <TraceBlock title="Prompt sent to the model" text={trace.prompt} />
            <TraceBlock
              title="Model proposal (raw output)"
              text={JSON.stringify(trace.llm_output, null, 2)}
            />
            <TraceBlock
              title="Guard verdict"
              text={JSON.stringify(trace.verification, null, 2)}
            />
            <TraceBlock
              title="Grounded context"
              text={JSON.stringify(trace.context, null, 2)}
            />
          </div>
        </details>
      )}
    </section>
  );
}

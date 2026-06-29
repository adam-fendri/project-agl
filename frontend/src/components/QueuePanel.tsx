import { useState } from "react";
import { useAppData } from "../data/store";
import type { Decision, Outcome } from "../api/types";
import { HandledRow, QueueRow } from "./QueueRow";
import { Alert, FileText, Inbox } from "./ui/icons";

type Tab = "queue" | "posted" | "handled";

interface SectionDef {
  key: Outcome;
  title: string;
  subtitle: string;
  tone: string;
}

const SECTIONS: SectionDef[] = [
  { key: "anomaly", title: "Anomalies", subtitle: "Resolve before anything posts", tone: "danger" },
  { key: "review", title: "Needs review", subtitle: "Confirm the agent's call", tone: "warning" },
  {
    key: "request_document",
    title: "Document requests",
    subtitle: "Missing a material document",
    tone: "info",
  },
];

function QueueSections({ queue }: { queue: Decision[] }) {
  if (queue.length === 0) {
    return (
      <div className="listempty">
        <Inbox size={26} />
        <p>The review queue is clear.</p>
        <span>Everything the agent was sure of has posted automatically.</span>
      </div>
    );
  }
  return (
    <div className="sections">
      {SECTIONS.map((section) => {
        const rows = queue.filter((decision) => decision.outcome === section.key);
        if (rows.length === 0) {
          return null;
        }
        return (
          <div key={section.key} className="section">
            <div className={`section__head section__head--${section.tone}`}>
              <span className="section__title">{section.title}</span>
              <span className="section__count">{rows.length}</span>
              <span className="section__sub">{section.subtitle}</span>
            </div>
            <div className="section__rows">
              {rows.map((decision) => (
                <QueueRow key={decision.transaction_id} decision={decision} />
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function QueuePanel() {
  const { queue, posted, handled, engineHasRun } = useAppData();
  const [tab, setTab] = useState<Tab>("queue");

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: "queue", label: "Queue", count: queue.length },
    { key: "posted", label: "Posted", count: posted.length },
    { key: "handled", label: "Handled", count: handled.length },
  ];

  return (
    <aside className="queuepanel">
      <div className="tabs" role="tablist">
        {tabs.map((entry) => (
          <button
            key={entry.key}
            type="button"
            role="tab"
            aria-selected={tab === entry.key}
            className={`tab${tab === entry.key ? " is-active" : ""}`}
            onClick={() => setTab(entry.key)}
          >
            {entry.label}
            <span className="tab__count">{entry.count}</span>
          </button>
        ))}
      </div>

      <div className="queuepanel__body">
        {!engineHasRun ? (
          <div className="listempty">
            <Inbox size={26} />
            <p>No decisions yet.</p>
            <span>Run the engine to categorise and reconcile the transactions.</span>
          </div>
        ) : tab === "queue" ? (
          <QueueSections queue={queue} />
        ) : tab === "posted" ? (
          posted.length === 0 ? (
            <div className="listempty">
              <FileText size={26} />
              <p>Nothing posted yet.</p>
            </div>
          ) : (
            <div className="section__rows section__rows--flat">
              {posted.map((decision) => (
                <QueueRow key={decision.transaction_id} decision={decision} />
              ))}
            </div>
          )
        ) : handled.length === 0 ? (
          <div className="listempty">
            <Alert size={26} />
            <p>Nothing flagged or requested yet.</p>
          </div>
        ) : (
          <div className="section__rows section__rows--flat">
            {handled.map((record) => (
              <HandledRow
                key={record.transaction_id}
                transactionId={record.transaction_id}
                vendor={record.vendor}
                account={record.account}
                action={record.action}
              />
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

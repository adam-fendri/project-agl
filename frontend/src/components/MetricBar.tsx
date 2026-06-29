import { useAppData } from "../data/store";
import { formatPercent } from "../lib/format";
import type { Tone } from "../lib/labels";
import { Shield } from "./ui/icons";

interface Stat {
  label: string;
  value: string;
  tone: Tone;
  hint: string;
}

export function MetricBar() {
  const { metrics, engineHasRun } = useAppData();

  if (!metrics || !engineHasRun) {
    return (
      <section className="metricbar metricbar--empty">
        <span className="metricbar__placeholder">
          Run the engine to populate auto-posting, review and accuracy figures.
        </span>
      </section>
    );
  }

  const counts = metrics.counts;
  const stats: Stat[] = [
    {
      label: "Auto-posted",
      value: String(counts.auto_post),
      tone: "success",
      hint: "Posted automatically — both confidences high and the guard clean",
    },
    {
      label: "Needs review",
      value: String(counts.review),
      tone: "warning",
      hint: "Deferred for the accountant to confirm",
    },
    {
      label: "Anomalies",
      value: String(counts.anomaly),
      tone: "danger",
      hint: "Held for resolution before posting",
    },
    {
      label: "Document requests",
      value: String(counts.request_document),
      tone: "info",
      hint: "Missing a material invoice or bill",
    },
    {
      label: "Categorisation accuracy",
      value: formatPercent(metrics.categorization_accuracy),
      tone: "neutral",
      hint: "Share of transactions booked to the correct account",
    },
  ];

  const cleanReconciliation = metrics.false_confidence_reconciliation === 0;

  return (
    <section className="metricbar">
      <div className="metricbar__stats">
        {stats.map((stat) => (
          <div key={stat.label} className={`stat stat--${stat.tone}`} title={stat.hint}>
            <span className="stat__value">{stat.value}</span>
            <span className="stat__label">{stat.label}</span>
          </div>
        ))}
      </div>
      <div className={`trustchip ${cleanReconciliation ? "trustchip--ok" : "trustchip--alert"}`}>
        <Shield size={18} />
        <span className="trustchip__text">
          <strong>
            {cleanReconciliation
              ? "0 confidently-wrong on reconciliation"
              : `${metrics.false_confidence_reconciliation} confidently-wrong on reconciliation`}
          </strong>
          <span>{counts.reconciliation_correct}/{counts.reconciliation_total} document matches verified</span>
        </span>
      </div>
    </section>
  );
}

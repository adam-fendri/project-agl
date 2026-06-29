import { useAppData } from "./data/store";
import { ClientHeader } from "./components/ClientHeader";
import { MetricBar } from "./components/MetricBar";
import { QueuePanel } from "./components/QueuePanel";
import { DecisionCard } from "./components/DecisionCard";
import { RunControl, RunProgress } from "./components/RunControl";
import { Toasts } from "./components/ui/Toasts";
import { Spinner } from "./components/ui/Spinner";
import { Alert, Check, FileText, Inbox, Sparkles } from "./components/ui/icons";

function EmptyHero() {
  const { customer } = useAppData();
  return (
    <div className="hero">
      <span className="hero__icon">
        <Sparkles size={26} />
      </span>
      <h2 className="hero__title">
        Ready to review {customer ? customer.name : "the client"}&rsquo;s books
      </h2>
      <p className="hero__lead">
        The agent categorises every bank transaction to the chart of accounts, reconciles it against
        the open invoices and bills, and rates two independent confidences. It posts what it is sure
        of and hands you the rest, ranked by where your attention is worth most.
      </p>
      <div className="hero__legend">
        <div className="hero__legend-item">
          <span className="dot dot--success" /> Auto-posted when both confidences are high
        </div>
        <div className="hero__legend-item">
          <span className="dot dot--warning" /> Deferred for review when anything is uncertain
        </div>
        <div className="hero__legend-item">
          <span className="dot dot--danger" /> Held as an anomaly when a guard check fails
        </div>
        <div className="hero__legend-item">
          <span className="dot dot--info" /> Document requested when a material bill is missing
        </div>
      </div>
      <div className="hero__cta">
        <RunControl />
      </div>
    </div>
  );
}

function DetailEmpty() {
  return (
    <div className="detailempty">
      <span className="detailempty__icon">
        <Inbox size={28} />
      </span>
      <p>Select a transaction from the queue to open its decision card.</p>
      <div className="detailempty__legend">
        <span>
          <Alert size={14} /> Anomalies
        </span>
        <span>
          <FileText size={14} /> Document requests
        </span>
        <span>
          <Check size={14} /> Needs review
        </span>
      </div>
    </div>
  );
}

export function App() {
  const { bootLoading, bootError, engineHasRun, selectedId } = useAppData();

  if (bootLoading) {
    return (
      <div className="boot">
        <Spinner size={28} />
        <span>Loading the console…</span>
      </div>
    );
  }

  if (bootError) {
    return (
      <div className="boot boot--error">
        <Alert size={28} />
        <span>Could not reach the backend.</span>
        <code>{bootError}</code>
      </div>
    );
  }

  return (
    <div className="app">
      <ClientHeader />
      <RunProgress />
      <MetricBar />
      <main className="workspace">
        <QueuePanel />
        <section className="detail">
          {!engineHasRun ? (
            <EmptyHero />
          ) : selectedId ? (
            <DecisionCard />
          ) : (
            <DetailEmpty />
          )}
        </section>
      </main>
      <Toasts />
    </div>
  );
}

import type { Decision } from "../api/types";
import { humanizeSignal, signalTone } from "../lib/signals";
import { Alert, Check, Info } from "./ui/icons";

function SignalIcon({ tone }: { tone: "success" | "warning" | "danger" }) {
  if (tone === "success") {
    return <Check size={15} />;
  }
  if (tone === "danger") {
    return <Alert size={15} />;
  }
  return <Info size={15} />;
}

export function Evidence({ decision }: { decision: Decision }) {
  if (decision.confidence_signals.length === 0) {
    return null;
  }
  return (
    <section className="cardsection">
      <div className="cardsection__head">
        <h3>Why</h3>
        <span className="cardsection__sub">What the agent and the guard verified</span>
      </div>
      <ul className="signals">
        {decision.confidence_signals.map((token) => {
          const tone = signalTone(token);
          return (
            <li key={token} className={`signal signal--${tone}`}>
              <span className="signal__icon">
                <SignalIcon tone={tone} />
              </span>
              <span className="signal__text">{humanizeSignal(token)}</span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

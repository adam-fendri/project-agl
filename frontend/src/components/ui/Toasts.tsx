import { useAppData } from "../../data/store";
import { Alert, Check, Close, Info } from "./icons";

function ToastIcon({ tone }: { tone: "info" | "success" | "danger" }) {
  if (tone === "success") {
    return <Check size={16} />;
  }
  if (tone === "danger") {
    return <Alert size={16} />;
  }
  return <Info size={16} />;
}

export function Toasts() {
  const { toasts, dismissToast } = useAppData();
  if (toasts.length === 0) {
    return null;
  }
  return (
    <div className="toasts" role="region" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast--${toast.tone}`}>
          <span className="toast__icon">
            <ToastIcon tone={toast.tone} />
          </span>
          <span className="toast__msg">{toast.message}</span>
          <button
            type="button"
            className="toast__close"
            onClick={() => dismissToast(toast.id)}
            aria-label="Dismiss"
          >
            <Close size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}

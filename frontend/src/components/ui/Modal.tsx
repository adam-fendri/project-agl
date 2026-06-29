import { useEffect, type ReactNode } from "react";
import { Close } from "./icons";

interface ModalProps {
  title: string;
  children: ReactNode;
  onClose: () => void;
  footer?: ReactNode;
  width?: number;
}

export function Modal({ title, children, onClose, footer, width }: ModalProps) {
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div className="overlay" onMouseDown={onClose}>
      <div
        className="modal"
        style={width ? { maxWidth: width } : undefined}
        onMouseDown={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="modal__head">
          <h3>{title}</h3>
          <button type="button" className="iconbtn" onClick={onClose} aria-label="Close">
            <Close size={16} />
          </button>
        </div>
        <div className="modal__body">{children}</div>
        {footer && <div className="modal__foot">{footer}</div>}
      </div>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";

export function useOutsideClick<T extends HTMLElement>(
  onClose: () => void,
  active: boolean,
) {
  const ref = useRef<T | null>(null);
  useEffect(() => {
    if (!active) {
      return;
    }
    function handlePointer(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        onClose();
      }
    }
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("mousedown", handlePointer);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handlePointer);
      document.removeEventListener("keydown", handleKey);
    };
  }, [onClose, active]);
  return ref;
}

export function useElapsedSeconds(active: boolean): number {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!active) {
      setSeconds(0);
      return;
    }
    const start = Date.now();
    const timer = window.setInterval(() => {
      setSeconds(Math.floor((Date.now() - start) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [active]);
  return seconds;
}

import { signedAmount } from "../../lib/format";
import { ArrowDown, ArrowUp } from "./icons";

interface MoneyProps {
  value: string | number;
  size?: "sm" | "md" | "lg";
  showDirection?: boolean;
}

export function Money({ value, size = "md", showDirection = true }: MoneyProps) {
  const { direction, display } = signedAmount(value);
  const sign = direction === "out" ? "-" : direction === "in" ? "+" : "";
  return (
    <span className={`money money--${direction} money--${size}`}>
      {showDirection && direction === "in" && <ArrowUp size={14} className="money__arrow" />}
      {showDirection && direction === "out" && <ArrowDown size={14} className="money__arrow" />}
      <span className="money__value">
        {sign} {display}
      </span>
    </span>
  );
}

export function DirectionTag({ value }: { value: string | number }) {
  const { direction } = signedAmount(value);
  if (direction === "in") {
    return <span className="dirtag dirtag--in">Money in</span>;
  }
  if (direction === "out") {
    return <span className="dirtag dirtag--out">Money out</span>;
  }
  return null;
}

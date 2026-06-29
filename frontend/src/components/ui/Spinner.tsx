export function Spinner({ size = 18 }: { size?: number }) {
  return (
    <span
      className="spinner"
      style={{ width: size, height: size }}
      aria-label="Loading"
      role="status"
    />
  );
}

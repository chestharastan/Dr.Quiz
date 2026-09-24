export default function BrandMark({ size = "md" }: { size?: "md" | "lg" }) {
  return (
    <span aria-hidden="true" className={`brand-mark ${size === "lg" ? "brand-mark-lg" : ""}`}>
      Q
    </span>
  );
}

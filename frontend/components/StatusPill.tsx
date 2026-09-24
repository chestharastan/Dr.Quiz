import type { AdminQuestion } from "@/lib/api";

// One word for where a question stands: deleted beats needs-review beats active.
export default function StatusPill({ question }: { question: AdminQuestion }) {
  if (!question.is_active) return <span className="status-pill status-deleted">Deleted</span>;
  if (question.needs_review) return <span className="status-pill status-review">Review</span>;
  return <span className="status-pill status-active">Active</span>;
}

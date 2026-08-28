"use client";

import type { AdminQuestion } from "@/lib/api";

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-[var(--hairline)] px-2 py-0.5 text-[11px] font-medium text-[var(--muted)]">
      {children}
    </span>
  );
}

export default function AdminQuestionTable({
  questions,
  onDelete,
}: {
  questions: AdminQuestion[];
  onDelete: (sourceFile: string, questionNumber: number) => void;
}) {
  if (questions.length === 0) {
    return <p className="p-3 text-sm text-[var(--muted)]">No questions match the current filters.</p>;
  }

  return (
    <>
      {/* Mobile: stacked cards */}
      <div className="flex flex-col gap-3 sm:hidden">
        {questions.map((q) => (
          <div key={q.id} className="glass-card flex flex-col gap-2 p-4">
            <div className="flex items-center justify-between gap-2 text-[12px] text-[var(--muted)]">
              <span className="truncate">
                {q.source_file} · #{q.question_number}
              </span>
              {q.is_active && (
                <button
                  onClick={() => onDelete(q.source_file, q.question_number)}
                  className="shrink-0 text-[12px] font-medium text-incorrect"
                >
                  Delete
                </button>
              )}
            </div>
            <p className="text-[14px] leading-snug">{q.question_text}</p>
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge>Answer {q.correct_answer}</Badge>
              <Badge>{q.is_active ? "Active" : "Inactive"}</Badge>
              <Badge>{q.needs_review ? "⚠ Review" : "OK"}</Badge>
              {q.ocr_confidence !== null && <Badge>Conf. {q.ocr_confidence.toFixed(2)}</Badge>}
            </div>
          </div>
        ))}
      </div>

      {/* Tablet/desktop: table */}
      <div className="glass-card hidden overflow-x-auto p-2 sm:block">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-zinc-300 text-left dark:border-zinc-700">
              <th className="p-2">File</th>
              <th className="p-2">#</th>
              <th className="p-2">Question</th>
              <th className="p-2">Answer</th>
              <th className="p-2">Active</th>
              <th className="p-2">Review</th>
              <th className="p-2">Conf.</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {questions.map((q) => (
              <tr key={q.id} className="border-b border-zinc-200 align-top dark:border-zinc-800">
                <td className="p-2 whitespace-nowrap">{q.source_file}</td>
                <td className="p-2">{q.question_number}</td>
                <td className="p-2 max-w-xl">{q.question_text}</td>
                <td className="p-2">{q.correct_answer}</td>
                <td className="p-2">{q.is_active ? "yes" : "no"}</td>
                <td className="p-2">{q.needs_review ? "⚠ review" : "ok"}</td>
                <td className="p-2">{q.ocr_confidence !== null ? q.ocr_confidence.toFixed(2) : "—"}</td>
                <td className="p-2">
                  {q.is_active && (
                    <button
                      onClick={() => onDelete(q.source_file, q.question_number)}
                      className="rounded bg-red-600 px-3 py-1 text-white hover:bg-red-700"
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

import { qaImageUrl, type QaQuizQuestion, type SubmitResult } from "@/lib/api";

export default function QaScoreResult({
  result,
  questions,
  onRetake,
}: {
  result: SubmitResult;
  questions: QaQuizQuestion[];
  onRetake: () => void;
}) {
  const questionsById = new Map(questions.map((q) => [q.id, q]));
  const pct = result.total > 0 ? Math.round((result.score / result.total) * 100) : 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-card flex flex-col items-center gap-2 p-8 text-center">
        <p className="text-[13px] font-medium uppercase tracking-wide text-[var(--muted)]">
          Your score
        </p>
        <p className="text-5xl font-bold tracking-[-0.02em]">
          {result.score}
          <span className="text-2xl text-[var(--muted)]"> / {result.total}</span>
        </p>
        <p className="text-[15px] text-[var(--muted)]">{pct}% correct</p>
      </div>

      <ul className="flex flex-col gap-3">
        {result.per_question_results.map((r, idx) => {
          const q = questionsById.get(r.question_id);
          if (!q) return null;
          return (
            <li key={r.question_id} className="glass-card flex items-center gap-3 p-3">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                  r.is_correct ? "badge-correct text-correct" : "badge-incorrect text-incorrect"
                }`}
              >
                {idx + 1}
              </span>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={qaImageUrl(q.question_image)}
                alt={`Question ${idx + 1}`}
                className="h-16 w-16 shrink-0 rounded-lg border border-[var(--hairline)] bg-white object-contain"
              />
              <p className="text-[13px] text-[var(--muted)]">
                Your answer:{" "}
                <strong className={r.is_correct ? "text-correct" : "text-incorrect"}>
                  {r.selected_answer}
                </strong>
                {!r.is_correct && (
                  <>
                    {" "}
                    · Correct: <strong className="text-correct">{r.correct_answer}</strong>
                  </>
                )}
              </p>
            </li>
          );
        })}
      </ul>

      <button onClick={onRetake} className="btn-primary inline-flex w-fit items-center justify-center">
        Retake
      </button>
    </div>
  );
}

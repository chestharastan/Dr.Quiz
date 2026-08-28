import type { QuizQuestion, SubmitResult } from "@/lib/api";

export default function ScoreResult({
  result,
  questions,
  onRetake,
}: {
  result: SubmitResult;
  questions: QuizQuestion[];
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
            <li key={r.question_id} className="glass-card p-4">
              <div className="flex items-start gap-3">
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                    r.is_correct ? "badge-correct text-correct" : "badge-incorrect text-incorrect"
                  }`}
                >
                  {idx + 1}
                </span>
                <div className="flex-1">
                  <p className="text-[15px] font-medium leading-snug">{q.question_text}</p>
                  <p className="mt-1 text-[13px] text-[var(--muted)]">
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
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      <button onClick={onRetake} className="btn-primary inline-flex w-fit items-center justify-center">
        Retake this task
      </button>
    </div>
  );
}

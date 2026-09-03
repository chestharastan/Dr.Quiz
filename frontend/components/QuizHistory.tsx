import type { QuizAttempt } from "@/lib/api";

export default function QuizHistory({ attempts }: { attempts: QuizAttempt[] }) {
  return (
    <section className="mt-5 flex flex-col gap-3">
      <div>
        <h2 className="text-[16px] font-semibold">Attempt history</h2>
        <p className="text-[13px] text-[var(--muted)]">Your 50 most recent submitted tasks.</p>
      </div>

      {attempts.length === 0 ? (
        <div className="glass-card p-5 text-[13px] text-[var(--muted)]">
          No submitted attempts yet.
        </div>
      ) : (
        attempts.map((attempt) => {
          const percent = attempt.total > 0 ? Math.round((attempt.score / attempt.total) * 100) : 0;
          return (
            <details key={attempt.id} className="glass-card group p-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="truncate text-[15px] font-semibold">{attempt.task_name}</p>
                  <p suppressHydrationWarning className="text-[12px] text-[var(--muted)]">
                    {new Date(attempt.submitted_at).toLocaleString()}
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-[15px] font-semibold">
                    {attempt.score} / {attempt.total}
                  </p>
                  <p className="text-[12px] text-[var(--muted)]">{percent}%</p>
                </div>
              </summary>

              <ul className="mt-4 flex flex-col gap-3 border-t border-[var(--border)] pt-4">
                {attempt.per_question_results.map((answer, index) => (
                  <li key={`${attempt.id}:${answer.question_id}`} className="text-[13px]">
                    <p className="font-medium leading-snug">
                      {index + 1}. {answer.question_text}
                    </p>
                    <p className="mt-1 text-[var(--muted)]">
                      Your answer:{" "}
                      <strong className={answer.is_correct ? "text-correct" : "text-incorrect"}>
                        {answer.selected_answer}
                      </strong>
                      {!answer.is_correct && (
                        <>
                          {" "}
                          · Correct: <strong className="text-correct">{answer.correct_answer}</strong>
                        </>
                      )}
                    </p>
                  </li>
                ))}
              </ul>
            </details>
          );
        })
      )}
    </section>
  );
}

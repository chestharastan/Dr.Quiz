import { qaImageUrl, qaQuestionLabel, type QaQuizQuestion, type SubmitResult } from "@/lib/api";

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
          // Choices are shown in a random on-screen order during the quiz
          // (see QaImageQuizForm's per-question shuffle), so the raw A/B/C/D
          // letters here don't correspond to what was actually labeled A/B/C/D
          // on screen when this was answered -- showing the choice's own
          // image instead sidesteps that mismatch entirely, since the image
          // is unambiguous regardless of which letter it was shuffled to.
          const selectedChoice = q.choices.find((c) => c.label === r.selected_answer);
          const correctChoice = q.choices.find((c) => c.label === r.correct_answer);
          return (
            <li key={r.question_id} className="glass-card flex flex-col gap-2.5 p-3">
              <div className="flex items-center gap-2">
                <span
                  className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                    r.is_correct ? "badge-correct text-correct" : "badge-incorrect text-incorrect"
                  }`}
                >
                  {idx + 1}
                </span>
                <span className="min-w-0 flex-1 text-[12px] font-medium text-[var(--muted)]">
                  {qaQuestionLabel(q)}
                </span>
              </div>

              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={qaImageUrl(q.question_image)}
                alt={`Question ${idx + 1}`}
                className="w-full rounded-lg border border-[var(--hairline)] bg-white object-contain"
              />

              <div className="flex flex-col gap-1.5">
                <div className="flex items-center gap-2">
                  <span className={`text-[12px] shrink-0 ${r.is_correct ? "text-correct" : "text-incorrect"}`}>
                    Your answer:
                  </span>
                  {selectedChoice ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={qaImageUrl(selectedChoice.image)}
                      alt="Your answer"
                      className="h-9 w-auto max-w-full rounded border border-[var(--hairline)] bg-white object-contain"
                    />
                  ) : (
                    <span className="text-[13px] text-[var(--muted)]">(not answered)</span>
                  )}
                </div>
                {!r.is_correct && correctChoice && (
                  <div className="flex items-center gap-2">
                    <span className="text-[12px] shrink-0 text-correct">Correct:</span>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={qaImageUrl(correctChoice.image)}
                      alt="Correct answer"
                      className="h-9 w-auto max-w-full rounded border border-[var(--hairline)] bg-white object-contain"
                    />
                  </div>
                )}
              </div>
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

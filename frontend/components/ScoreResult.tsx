import type { SubmitResult } from "@/lib/api";
import { choiceText, shownLetter, type ShuffledQuestion } from "@/lib/shuffle";

export default function ScoreResult({
  result,
  questions,
  onNewQuiz,
}: {
  result: SubmitResult;
  questions: ShuffledQuestion[];
  onNewQuiz: () => void;
}) {
  const questionsById = new Map(questions.map((q) => [q.id, q]));
  const pct = result.total > 0 ? Math.round((result.score / result.total) * 100) : 0;

  return (
    <div className="flex flex-col gap-6">
      <div className="glass-card flex flex-col items-center gap-2 p-8 text-center">
        <p className="text-[13px] font-medium tracking-wide text-[var(--muted)] uppercase">Your score</p>
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
          // Letters as they were shown in this quiz (the choices were shuffled), with the answer text
          const answer = (letter: string) => `${shownLetter(q, letter)}. ${choiceText(q, letter)}`;
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
                  <p className="text-[15px] leading-snug font-medium">{q.question_text}</p>
                  <p className="mt-1.5 text-[13px] text-[var(--muted)]">
                    Your answer:{" "}
                    <strong className={r.is_correct ? "text-correct" : "text-incorrect"}>
                      {answer(r.selected_answer)}
                    </strong>
                  </p>
                  {!r.is_correct && (
                    <p className="text-[13px] text-[var(--muted)]">
                      Correct: <strong className="text-correct">{answer(r.correct_answer)}</strong>
                    </p>
                  )}
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      <button onClick={onNewQuiz} className="btn-primary w-fit">
        New quiz
      </button>
    </div>
  );
}

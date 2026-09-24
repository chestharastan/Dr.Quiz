"use client";

import { useEffect, useRef } from "react";
import { LETTERS, choiceText, type ShuffledQuestion } from "@/lib/shuffle";

const ADVANCE_DELAY_MS = 280;

export default function QuizForm({
  questions,
  currentIndex,
  answers,
  onAnswer,
  onNext,
  onPrev,
  onSubmit,
}: {
  questions: ShuffledQuestion[];
  currentIndex: number;
  answers: Record<string, string>;
  onAnswer: (questionId: string, choice: string) => void;
  onNext: () => void;
  onPrev: () => void;
  onSubmit: () => void;
}) {
  const question = questions[currentIndex];
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === questions.length - 1;
  const selected = answers[question.id];
  const answeredCount = Object.keys(answers).length;
  const progress = ((currentIndex + 1) / questions.length) * 100;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [currentIndex]);

  function handleChoice(key: string) {
    onAnswer(question.id, key);
    if (!isLast) {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => onNext(), ADVANCE_DELAY_MS);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between text-[13px] font-medium text-[var(--muted)]">
        <span>
          Question {currentIndex + 1} of {questions.length}
        </span>
        <span>{answeredCount} answered</span>
      </div>

      <div className="h-1 w-full overflow-hidden rounded-full bg-[var(--track)]">
        <div
          className="h-full rounded-full bg-[var(--accent)] transition-[width] duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div key={question.id} className="glass-card animate-card-in p-6 sm:p-7">
        <p className="text-[17px] font-semibold leading-snug tracking-[-0.01em]">
          {question.question_text}
        </p>

        <div className="mt-5 flex flex-col gap-2">
          {/* Shown in this question's shuffled order; the answer keeps its original letter for grading. */}
          {question.order.map((letter, position) => {
            const isSelected = selected === letter;
            return (
              <button
                key={letter}
                type="button"
                onClick={() => handleChoice(letter)}
                className={`choice-row ${isSelected ? "choice-row-selected" : ""}`}
              >
                <span className="choice-letter">{LETTERS[position]}</span>
                <span className="flex-1 text-left">{choiceText(question, letter)}</span>
                {isSelected && (
                  <svg
                    viewBox="0 0 20 20"
                    className="h-5 w-5 shrink-0 text-[var(--accent)]"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.7 5.3a1 1 0 0 1 0 1.4l-7.4 7.4a1 1 0 0 1-1.4 0L3.3 9.5a1 1 0 1 1 1.4-1.4l3.9 3.9 6.7-6.7a1 1 0 0 1 1.4 0Z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex items-center justify-between">
        <button type="button" onClick={onPrev} disabled={isFirst} className="btn-ghost">
          Previous
        </button>

        {isLast ? (
          <button type="button" onClick={onSubmit} disabled={!selected} className="btn-primary">
            Submit quiz
          </button>
        ) : (
          <button type="button" onClick={onNext} disabled={!selected} className="btn-ghost">
            Next
          </button>
        )}
      </div>
    </div>
  );
}

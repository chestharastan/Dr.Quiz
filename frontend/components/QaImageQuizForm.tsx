"use client";

import { useEffect, useMemo, useRef } from "react";
import { qaImageUrl, type QaQuizQuestion } from "@/lib/api";

const DISPLAY_LABELS = ["A", "B", "C", "D"] as const;
const ADVANCE_DELAY_MS = 280;

function shuffled<T>(items: T[]): T[] {
  const arr = [...items];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

export default function QaImageQuizForm({
  questions,
  currentIndex,
  answers,
  onAnswer,
  onNext,
  onPrev,
  onSubmit,
}: {
  questions: QaQuizQuestion[];
  currentIndex: number;
  answers: Record<string, string>;
  onAnswer: (questionId: string, sourceLabel: string) => void;
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

  // Choices arrive in their original source order (A-D); reshuffle per question
  // so the correct answer isn't always in the same on-screen position.
  const displayChoices = useMemo(() => shuffled(question.choices), [question.id]);

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [currentIndex]);

  function handleChoice(sourceLabel: string) {
    onAnswer(question.id, sourceLabel);
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

      <div key={question.id} className="glass-card animate-card-in p-4 sm:p-5">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={qaImageUrl(question.question_image)}
          alt={`Question ${currentIndex + 1}`}
          className="w-full rounded-xl border border-[var(--hairline)]"
        />

        <div className="mt-5 grid grid-cols-2 gap-3">
          {displayChoices.map((choice, i) => {
            const displayLabel = DISPLAY_LABELS[i];
            const isSelected = selected === choice.label;
            return (
              <button
                key={choice.label}
                type="button"
                onClick={() => handleChoice(choice.label)}
                className={`choice-image-card ${isSelected ? "choice-image-card-selected" : ""}`}
              >
                <span className="choice-image-label">{displayLabel}.</span>
                <div className="choice-image-frame">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={qaImageUrl(choice.image)}
                    alt={`Choice ${displayLabel}`}
                    className="choice-image-img"
                  />
                </div>
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

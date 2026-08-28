"use client";

import { useEffect, useRef } from "react";
import { imageUrl, type ImageQuizQuestion } from "@/lib/api";

const CHOICE_KEYS = ["A", "B", "C", "D"] as const;
const ADVANCE_DELAY_MS = 280;

export default function ImageQuizForm({
  questions,
  currentIndex,
  answers,
  onAnswer,
  onNext,
  onPrev,
  onSubmit,
}: {
  questions: ImageQuizQuestion[];
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

      <div key={question.id} className="glass-card animate-card-in p-4 sm:p-5">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={imageUrl(question.image_path)}
          alt={`Question ${currentIndex + 1}`}
          className="w-full rounded-xl border border-[var(--hairline)]"
        />

        <div className="mt-5 grid grid-cols-4 gap-2">
          {CHOICE_KEYS.map((key) => {
            const isSelected = selected === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => handleChoice(key)}
                className={`choice-row justify-center text-[16px] font-semibold ${
                  isSelected ? "choice-row-selected" : ""
                }`}
              >
                {key}
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

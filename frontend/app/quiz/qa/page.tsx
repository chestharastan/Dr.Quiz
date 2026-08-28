"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchMe,
  fetchQaQuestions,
  submitQaQuiz,
  type AuthUser,
  type QaQuizQuestion,
  type SubmitResult,
} from "@/lib/api";
import QaImageQuizForm from "@/components/QaImageQuizForm";
import QaScoreResult from "@/components/QaScoreResult";

type Stage = "loading" | "setup" | "quiz" | "result" | "error";

const COUNT_PRESETS = [10, 20, 50, 100];

type PersistedSession = {
  stage: "quiz" | "result";
  count: number;
  questions: QaQuizQuestion[];
  answers: Record<string, string>;
  currentIndex: number;
  result?: SubmitResult;
};

function storageKey(userId: string) {
  return `quizdr:qa-session:v1:${userId}`;
}

export default function QaQuizPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [stage, setStage] = useState<Stage>("loading");
  const [count, setCount] = useState(20);
  const [questions, setQuestions] = useState<QaQuizQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      let me: AuthUser;
      try {
        me = await fetchMe();
      } catch {
        router.push("/login");
        return;
      }
      if (cancelled) return;
      setUser(me);

      let resumed = false;
      try {
        const raw = localStorage.getItem(storageKey(me.id));
        if (raw) {
          const saved: PersistedSession = JSON.parse(raw);
          if (saved.stage === "quiz" || saved.stage === "result") {
            setCount(saved.count);
            setQuestions(saved.questions);
            setAnswers(saved.answers);
            setCurrentIndex(saved.currentIndex);
            if (saved.result) setResult(saved.result);
            setStage(saved.stage);
            resumed = true;
          }
        }
      } catch {
        localStorage.removeItem(storageKey(me.id));
      }

      if (!resumed) setStage("setup");
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!user) return;
    const key = storageKey(user.id);
    if (stage === "quiz") {
      const session: PersistedSession = { stage, count, questions, answers, currentIndex };
      localStorage.setItem(key, JSON.stringify(session));
    } else if (stage === "result" && result) {
      const session: PersistedSession = { stage, count, questions, answers, currentIndex, result };
      localStorage.setItem(key, JSON.stringify(session));
    } else if (stage === "setup") {
      localStorage.removeItem(key);
    }
  }, [user, stage, count, questions, answers, currentIndex, result]);

  async function startQuiz() {
    setStage("loading");
    try {
      const qs = await fetchQaQuestions(count);
      setQuestions(qs);
      setAnswers({});
      setCurrentIndex(0);
      setResult(null);
      setStage(qs.length === 0 ? "error" : "quiz");
      if (qs.length === 0) setError("No active QA questions available.");
    } catch (e) {
      setError(String(e));
      setStage("error");
    }
  }

  function handleAnswer(questionId: string, choice: string) {
    setAnswers((prev) => ({ ...prev, [questionId]: choice }));
  }

  function goNext() {
    setCurrentIndex((i) => Math.min(i + 1, questions.length - 1));
  }

  function goPrev() {
    setCurrentIndex((i) => Math.max(i - 1, 0));
  }

  function resetToSetup() {
    setQuestions([]);
    setAnswers({});
    setCurrentIndex(0);
    setResult(null);
    setStage("setup");
  }

  function handleExit() {
    if (window.confirm("Exit this quiz? Your progress will be lost.")) {
      resetToSetup();
    }
  }

  async function handleSubmitQuiz() {
    setStage("loading");
    try {
      const payload = questions
        .map((q) => ({ question_id: q.id, selected_answer: answers[q.id] }))
        .filter((a) => a.selected_answer);
      const res = await submitQaQuiz(payload);
      setResult(res);
      setStage("result");
    } catch (e) {
      setError(String(e));
      setStage("error");
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/quiz" className="text-[13px] font-medium text-[var(--muted)] hover:text-[var(--foreground)]">
            ← Quiz
          </Link>
          <h1 className="text-[20px] font-semibold tracking-[-0.02em]">QA Image Quiz</h1>
        </div>
        {stage === "quiz" && (
          <button
            onClick={handleExit}
            className="text-[13px] font-medium text-[var(--muted)] hover:text-[var(--foreground)]"
          >
            Exit
          </button>
        )}
      </div>

      {stage === "loading" && (
        <div className="glass-card p-8 text-center text-[15px] text-[var(--muted)]">Loading…</div>
      )}

      {stage === "setup" && (
        <div className="glass-card flex flex-col gap-6 p-7 sm:p-8">
          <div>
            <h2 className="text-[15px] font-semibold">Number of questions</h2>
            <p className="mt-1 text-[13px] text-[var(--muted)]">
              Pick a preset or enter a custom amount. Each choice is its own image, shown in a random
              order so the correct answer isn&apos;t always in the same spot.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            {COUNT_PRESETS.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setCount(n)}
                className={`chip ${count === n ? "chip-selected" : ""}`}
              >
                {n}
              </button>
            ))}
          </div>

          <label className="flex flex-col gap-1.5">
            <span className="text-[13px] font-medium text-[var(--muted)]">Custom amount</span>
            <input
              type="number"
              min={1}
              max={1662}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="input-field w-32"
            />
          </label>

          <button
            onClick={startQuiz}
            className="btn-primary inline-flex w-fit items-center justify-center"
          >
            Start Quiz
          </button>
        </div>
      )}

      {stage === "error" && (
        <div className="glass-card flex flex-col gap-4 p-7 text-center">
          <p className="text-[15px] text-incorrect">{error}</p>
          <button
            onClick={resetToSetup}
            className="btn-ghost inline-flex w-fit items-center justify-center self-center"
          >
            Back to setup
          </button>
        </div>
      )}

      {stage === "quiz" && (
        <QaImageQuizForm
          questions={questions}
          currentIndex={currentIndex}
          answers={answers}
          onAnswer={handleAnswer}
          onNext={goNext}
          onPrev={goPrev}
          onSubmit={handleSubmitQuiz}
        />
      )}

      {stage === "result" && result && (
        <QaScoreResult result={result} questions={questions} onRetake={resetToSetup} />
      )}
    </main>
  );
}

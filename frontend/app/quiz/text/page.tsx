"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchAvailableTasks,
  fetchMe,
  fetchQuizQuestions,
  submitQuiz,
  type AuthUser,
  type QuizQuestion,
  type SubmitResult,
  type Task,
} from "@/lib/api";
import QuizForm from "@/components/QuizForm";
import ScoreResult from "@/components/ScoreResult";

type Stage = "loading" | "pick-task" | "quiz" | "result" | "error";

type PersistedSession = {
  stage: "quiz" | "result";
  taskId: string;
  taskName: string;
  questions: QuizQuestion[];
  answers: Record<string, string>;
  currentIndex: number;
  result?: SubmitResult;
};

function storageKey(userId: string) {
  return `quizdr:text-session:v1:${userId}`;
}

export default function TextQuizPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [stage, setStage] = useState<Stage>("loading");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [taskId, setTaskId] = useState<string>("");
  const [taskName, setTaskName] = useState<string>("");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
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
            setTaskId(saved.taskId);
            setTaskName(saved.taskName);
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

      if (!resumed) {
        try {
          const list = await fetchAvailableTasks();
          if (cancelled) return;
          setTasks(list);
          setStage("pick-task");
        } catch (e) {
          setError(String(e));
          setStage("error");
        }
      }
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
      const session: PersistedSession = { stage, taskId, taskName, questions, answers, currentIndex };
      localStorage.setItem(key, JSON.stringify(session));
    } else if (stage === "result" && result) {
      const session: PersistedSession = { stage, taskId, taskName, questions, answers, currentIndex, result };
      localStorage.setItem(key, JSON.stringify(session));
    } else if (stage === "pick-task") {
      localStorage.removeItem(key);
    }
  }, [user, stage, taskId, taskName, questions, answers, currentIndex, result]);

  async function startTask(task: Task) {
    setStage("loading");
    try {
      const qs = await fetchQuizQuestions(task.id);
      setTaskId(task.id);
      setTaskName(task.name);
      setQuestions(qs);
      setAnswers({});
      setCurrentIndex(0);
      setResult(null);
      setStage(qs.length === 0 ? "error" : "quiz");
      if (qs.length === 0) setError("No active questions available for this task.");
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

  async function backToPicker() {
    setQuestions([]);
    setAnswers({});
    setCurrentIndex(0);
    setResult(null);
    setStage("loading");
    try {
      setTasks(await fetchAvailableTasks());
      setStage("pick-task");
    } catch (e) {
      setError(String(e));
      setStage("error");
    }
  }

  function handleExit() {
    if (window.confirm("Exit this quiz? Your progress will be lost.")) {
      void backToPicker();
    }
  }

  async function handleSubmitQuiz() {
    setStage("loading");
    try {
      const payload = questions
        .map((q) => ({ question_id: q.id, selected_answer: answers[q.id] }))
        .filter((a) => a.selected_answer);
      const res = await submitQuiz(payload);
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
          <h1 className="text-[20px] font-semibold tracking-[-0.02em]">Text Quiz</h1>
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

      {stage === "pick-task" && (
        <div className="flex flex-col gap-3">
          {tasks.length === 0 && (
            <div className="glass-card p-7 text-center text-[15px] text-[var(--muted)]">
              No quiz tasks are available yet.
            </div>
          )}
          {tasks.map((t) => (
            <button
              key={t.id}
              onClick={() => startTask(t)}
              className="glass-card flex flex-col gap-1 p-5 text-left hover:opacity-90"
            >
              <span className="text-[15px] font-semibold">{t.name}</span>
              <span className="text-[13px] text-[var(--muted)]">
                {t.question_count} questions · {t.source_file ?? "All files"}
              </span>
            </button>
          ))}
        </div>
      )}

      {stage === "error" && (
        <div className="glass-card flex flex-col gap-4 p-7 text-center">
          <p className="text-[15px] text-incorrect">{error}</p>
          <button
            onClick={backToPicker}
            className="btn-ghost inline-flex w-fit items-center justify-center self-center"
          >
            Back
          </button>
        </div>
      )}

      {stage === "quiz" && (
        <QuizForm
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
        <ScoreResult result={result} questions={questions} onRetake={backToPicker} />
      )}
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  fetchAvailableTasks,
  fetchMe,
  fetchQuizHistory,
  fetchQuizQuestions,
  fetchQuizSources,
  logout,
  submitQuiz,
  type AuthUser,
  type QuizQuestion,
  type QuizAttempt,
  type SubmitResult,
  type Task,
} from "@/lib/api";
import QuizForm from "@/components/QuizForm";
import ScoreResult from "@/components/ScoreResult";
import QuizHistory from "@/components/QuizHistory";
import BrandMark from "@/components/BrandMark";
import { ChevronRightIcon } from "@/components/icons";
import { shuffleChoices, type ShuffledQuestion } from "@/lib/shuffle";

type Stage = "loading" | "pick-task" | "quiz" | "result" | "error";

const QUIZ_SIZES = [10, 20, 30, 50, 100];

type PersistedSession = {
  stage: "quiz" | "result";
  taskId: string; // "" for a quick quiz
  taskName: string;
  questions: ShuffledQuestion[];
  answers: Record<string, string>;
  currentIndex: number;
  result?: SubmitResult;
};

// v3: sessions store each question's shuffled choice order (v2 ones don't have it).
function storageKey(userId: string) {
  return `quizdr:text-session:v3:${userId}`;
}

// "Untitled 2.pdf" before "Untitled 10.pdf"
function sortSources(files: string[]) {
  return [...files].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
}

export default function QuizPage() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [stage, setStage] = useState<Stage>("loading");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [count, setCount] = useState(20);
  const [source, setSource] = useState("");
  const [history, setHistory] = useState<QuizAttempt[]>([]);
  const [taskId, setTaskId] = useState<string>("");
  const [taskName, setTaskName] = useState<string>("");
  const [questions, setQuestions] = useState<ShuffledQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [currentIndex, setCurrentIndex] = useState(0);
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      // Start every request at once so the page waits for one round trip to the backend, not two.
      const listsRequest = Promise.all([fetchAvailableTasks(), fetchQuizHistory(), fetchQuizSources()]);
      listsRequest.catch(() => {}); // not awaited when redirecting to login or resuming a saved quiz
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
          const [list, attempts, files] = await listsRequest;
          if (cancelled) return;
          setTasks(list);
          setHistory(attempts);
          setSources(sortSources(files));
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

  function beginQuiz(qs: QuizQuestion[], id: string, name: string) {
    if (qs.length === 0) {
      setError("No questions are available for this quiz.");
      setStage("error");
      return;
    }
    setTaskId(id);
    setTaskName(name);
    setQuestions(shuffleChoices(qs));
    setAnswers({});
    setCurrentIndex(0);
    setResult(null);
    setStage("quiz");
  }

  // Random questions without an admin-made task
  async function startQuickQuiz() {
    setStage("loading");
    try {
      const qs = await fetchQuizQuestions({ count, source_file: source || undefined });
      beginQuiz(qs, "", `Quick quiz · ${source || "All sources"}`);
    } catch (e) {
      setError(String(e));
      setStage("error");
    }
  }

  async function startTask(task: Task) {
    setStage("loading");
    try {
      beginQuiz(await fetchQuizQuestions({ task_id: task.id }), task.id, task.name);
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
      const [list, attempts, files] = await Promise.all([fetchAvailableTasks(), fetchQuizHistory(), fetchQuizSources()]);
      setTasks(list);
      setHistory(attempts);
      setSources(sortSources(files));
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

  async function handleLogout() {
    if (user) localStorage.removeItem(storageKey(user.id));
    await logout();
    router.push("/login");
  }

  async function handleSubmitQuiz() {
    setStage("loading");
    try {
      const payload = questions
        .map((q) => ({ question_id: q.id, selected_answer: answers[q.id] }))
        .filter((a) => a.selected_answer);
      const res = await submitQuiz(
        taskId ? { task_id: taskId, answers: payload } : { quiz_name: taskName, answers: payload }
      );
      setResult(res);
      setStage("result");
    } catch (e) {
      setError(String(e));
      setStage("error");
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-xl flex-col gap-6 px-4 py-6 sm:p-8">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <BrandMark />
          <div className="min-w-0 leading-tight">
            <h1 className="text-[20px] font-bold tracking-[-0.02em]">Quiz</h1>
            {user && <p className="truncate text-[13px] text-[var(--muted)]">Welcome, {user.name || user.username}</p>}
          </div>
        </div>
        {stage === "quiz" ? (
          <button onClick={handleExit} className="btn-ghost btn-sm">
            Exit
          </button>
        ) : (
          <div className="flex shrink-0 gap-2">
            {user?.role === "admin" && (
              <Link href="/admin" className="btn-ghost btn-sm">
                Admin
              </Link>
            )}
            <button onClick={handleLogout} className="btn-ghost btn-sm">
              Log out
            </button>
          </div>
        )}
      </div>

      {stage === "loading" && (
        <div className="glass-card p-8 text-center text-[15px] text-[var(--muted)]">Loading…</div>
      )}

      {stage === "pick-task" && (
        <div className="flex flex-col gap-6">
          <section className="glass-card flex flex-col gap-5 p-6">
            <div>
              <h2 className="text-[17px] font-semibold">Start a quiz</h2>
              <p className="mt-1 text-[13px] text-[var(--muted)]">
                Questions are picked at random, and the answers of each question are shuffled.
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-[13px] font-medium text-[var(--muted)]">Questions</span>
              <div className="flex flex-wrap gap-2">
                {QUIZ_SIZES.map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setCount(n)}
                    aria-pressed={count === n}
                    className={`chip min-w-12 ${count === n ? "chip-selected" : ""}`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
            <label className="flex flex-col gap-2">
              <span className="text-[13px] font-medium text-[var(--muted)]">Source</span>
              <select value={source} onChange={(e) => setSource(e.target.value)} className="input-field">
                <option value="">All sources</option>
                {sources.map((file) => (
                  <option key={file} value={file}>
                    {file}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" onClick={startQuickQuiz} className="btn-primary w-full">
              Start quiz
            </button>
          </section>

          {tasks.length > 0 && (
            <section className="flex flex-col gap-3">
              <h2 className="text-[16px] font-semibold">Assigned quizzes</h2>
              {tasks.map((t) => (
                <button
                  key={t.id}
                  onClick={() => startTask(t)}
                  className="glass-card flex items-center gap-3 p-5 text-left transition-transform active:scale-[0.99]"
                >
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <span className="text-[15px] font-semibold">{t.name}</span>
                    <span className="text-[13px] text-[var(--muted)]">
                      {t.question_count} questions · {t.source_file ?? "All sources"}
                    </span>
                  </div>
                  <ChevronRightIcon className="h-4 w-4 shrink-0 text-[var(--muted)]" />
                </button>
              ))}
            </section>
          )}

          <QuizHistory attempts={history} />
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
        <ScoreResult result={result} questions={questions} onNewQuiz={backToPicker} />
      )}
    </main>
  );
}

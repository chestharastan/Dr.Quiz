"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  deleteAdminQuestion,
  fetchAdminQuestions,
  fetchMe,
  logout,
  type AdminQuestion,
  type AuthUser,
} from "@/lib/api";
import AdminQuestionTable from "@/components/AdminQuestionTable";
import AdminExportButton from "@/components/AdminExportButton";
import AdminUserPanel from "@/components/AdminUserPanel";
import AdminTaskPanel from "@/components/AdminTaskPanel";

type Tab = "questions" | "users" | "tasks";

export default function AdminPage() {
  const router = useRouter();
  const [me, setMe] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [tab, setTab] = useState<Tab>("questions");

  const [questions, setQuestions] = useState<AdminQuestion[]>([]);
  const [sourceFile, setSourceFile] = useState("");
  const [questionNumber, setQuestionNumber] = useState("");
  const [includeInactive, setIncludeInactive] = useState(false);
  const [needsReviewOnly, setNeedsReviewOnly] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const user = await fetchMe();
        if (user.role !== "admin") {
          router.push("/quiz");
          return;
        }
        setMe(user);
      } catch {
        router.push("/login");
        return;
      }
      setAuthChecked(true);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (me && tab === "questions") void loadQuestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me, tab, includeInactive, needsReviewOnly]);

  async function loadQuestions() {
    setError("");
    try {
      const qs = await fetchAdminQuestions({
        source_file: sourceFile || undefined,
        question_number: questionNumber ? Number(questionNumber) : undefined,
        include_inactive: includeInactive,
        needs_review: needsReviewOnly ? true : undefined,
      });
      setQuestions(qs);
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleDelete(source_file: string, question_number: number) {
    if (!confirm(`Delete question #${question_number} from ${source_file}?`)) return;
    try {
      await deleteAdminQuestion(source_file, question_number);
      await loadQuestions();
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  if (!authChecked || !me) {
    return <main className="mx-auto flex max-w-5xl flex-col gap-6 p-8" />;
  }

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-6 p-4 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-[20px] font-semibold tracking-[-0.02em]">Admin</h1>
          <p className="text-[13px] text-[var(--muted)]">Signed in as {me.username}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 sm:gap-4">
          {tab === "questions" && <AdminExportButton />}
          <button
            onClick={handleLogout}
            className="text-[13px] font-medium text-[var(--muted)] hover:text-[var(--foreground)]"
          >
            Log out
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {(["questions", "users", "tasks"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`chip ${tab === t ? "chip-selected" : ""}`}>
            {t === "questions" ? "Questions" : t === "users" ? "Users" : "Tasks"}
          </button>
        ))}
      </div>

      {error && <p className="text-[13px] text-incorrect">{error}</p>}

      {tab === "questions" && (
        <>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void loadQuestions();
            }}
            className="glass-card flex flex-wrap items-end gap-3 p-5"
          >
            <label className="flex flex-col gap-1.5">
              <span className="text-[13px] font-medium text-[var(--muted)]">Source file</span>
              <input value={sourceFile} onChange={(e) => setSourceFile(e.target.value)} className="input-field" />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[13px] font-medium text-[var(--muted)]">Question number</span>
              <input
                type="number"
                value={questionNumber}
                onChange={(e) => setQuestionNumber(e.target.value)}
                className="input-field w-32"
              />
            </label>
            <label className="flex items-center gap-2 pb-2 text-[13px]">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(e) => setIncludeInactive(e.target.checked)}
              />
              Include deleted
            </label>
            <label className="flex items-center gap-2 pb-2 text-[13px]">
              <input
                type="checkbox"
                checked={needsReviewOnly}
                onChange={(e) => setNeedsReviewOnly(e.target.checked)}
              />
              Needs review only
            </label>
            <button type="submit" className="btn-ghost">
              Filter
            </button>
          </form>

          <AdminQuestionTable questions={questions} onDelete={handleDelete} />
        </>
      )}

      {tab === "users" && <AdminUserPanel />}
      {tab === "tasks" && <AdminTaskPanel />}
    </main>
  );
}

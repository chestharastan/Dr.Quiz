"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  deleteAdminQuestion,
  fetchAdminQuestions,
  fetchMe,
  fetchSourceFiles,
  logout,
  type AdminQuestion,
  type AuthUser,
} from "@/lib/api";
import AdminQuestionTable from "@/components/AdminQuestionTable";
import AdminShell, { type AdminTab } from "@/components/AdminShell";
import AdminExportButton from "@/components/AdminExportButton";
import AdminUserPanel from "@/components/AdminUserPanel";
import AdminTaskPanel from "@/components/AdminTaskPanel";
import Pagination from "@/components/Pagination";
import QuestionDrawer from "@/components/QuestionDrawer";
import { SearchIcon } from "@/components/icons";

const PAGE_SIZES = [10, 20, 30, 50, 100];
const PAGE_SIZE_KEY = "quizdr:admin-page-size";

function savedPageSize() {
  try {
    const size = Number(localStorage.getItem(PAGE_SIZE_KEY));
    if (PAGE_SIZES.includes(size)) return size;
  } catch {
    // no storage (or blocked): use the default
  }
  return 20;
}

type Drawer = { question: AdminQuestion; mode: "view" | "edit" };

export default function AdminPage() {
  const router = useRouter();
  const [me, setMe] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [tab, setTab] = useState<AdminTab>("questions");

  const [questions, setQuestions] = useState<AdminQuestion[]>([]);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(savedPageSize);
  const [drawer, setDrawer] = useState<Drawer | null>(null);
  const [loadingQuestions, setLoadingQuestions] = useState(true);
  const latestRequest = useRef(0);
  const tableTop = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState("");
  const [questionNumber, setQuestionNumber] = useState("");
  const [sourceFile, setSourceFile] = useState("");
  const [sourceFiles, setSourceFiles] = useState<string[]>([]);
  // What the list is filtered by: the typed values, applied shortly after typing stops.
  const [applied, setApplied] = useState({ search: "", questionNumber: "" });
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
  }, [me, tab, applied, sourceFile, page, pageSize]);

  useEffect(() => {
    if (search === applied.search && questionNumber === applied.questionNumber) return;
    const timer = setTimeout(() => {
      setApplied({ search, questionNumber });
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [search, questionNumber, applied]);

  useEffect(() => {
    if (!me) return;
    fetchSourceFiles()
      .then((files) => setSourceFiles([...files].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))))
      .catch((e) => setError(String(e)));
  }, [me]);

  async function loadQuestions() {
    const request = ++latestRequest.current;
    setError("");
    setLoadingQuestions(true);
    try {
      const res = await fetchAdminQuestions({
        search: applied.search.trim() || undefined,
        source_file: sourceFile || undefined,
        question_number: applied.questionNumber ? Number(applied.questionNumber) : undefined,
        page,
        page_size: pageSize,
      });
      if (request !== latestRequest.current) return; // a newer page was asked for meanwhile
      const lastPage = Math.max(1, Math.ceil(res.total / pageSize));
      if (page > lastPage) {
        setPage(lastPage); // e.g. the only question on the last page was deleted; the effect reloads
        return;
      }
      setQuestions(res.items);
      setTotalQuestions(res.total);
    } catch (e) {
      if (request === latestRequest.current) setError(String(e));
    } finally {
      if (request === latestRequest.current) setLoadingQuestions(false);
    }
  }

  const filtered = search !== "" || questionNumber !== "" || sourceFile !== "";

  function clearFilters() {
    setSearch("");
    setQuestionNumber("");
    setSourceFile("");
    setApplied({ search: "", questionNumber: "" });
    setPage(1);
  }

  function changePageSize(size: number) {
    setPageSize(size);
    setPage(1);
    try {
      localStorage.setItem(PAGE_SIZE_KEY, String(size));
    } catch {
      // storage blocked: the choice just isn't remembered
    }
  }

  function goToPage(next: number) {
    setPage(next);
    tableTop.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function handleDelete(question: AdminQuestion) {
    const { source_file, question_number } = question;
    if (!confirm(`Delete question #${question_number} from ${source_file}?`)) return;
    try {
      await deleteAdminQuestion(source_file, question_number);
      if (drawer?.question.id === question.id) setDrawer(null);
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
    return <div className="min-h-dvh" />;
  }

  const subtitle =
    tab === "users"
      ? "People who can sign in"
      : tab === "tasks"
        ? "Quizzes that users can start"
        : loadingQuestions && questions.length === 0
          ? "Loading…"
          : `${totalQuestions.toLocaleString()} ${filtered ? "matching " : ""}question${totalQuestions === 1 ? "" : "s"}`;

  return (
    <AdminShell user={me} tab={tab} onTabChange={setTab} onLogout={handleLogout}>
      <div className="flex flex-col gap-5">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-[28px] leading-tight font-bold tracking-[-0.025em] capitalize">{tab}</h1>
            <p className="mt-0.5 text-[14px] text-[var(--muted)]">{subtitle}</p>
          </div>
          {tab === "questions" && <AdminExportButton />}
        </header>

        {error && <p className="text-[13px] text-incorrect">{error}</p>}

        {tab === "questions" && (
          <>
            <form
              onSubmit={(e) => {
                // Enter applies the typed filters right away
                e.preventDefault();
                setApplied({ search, questionNumber });
                setPage(1);
              }}
              className="glass-card grid grid-cols-[1fr_6rem] gap-2 p-2.5 sm:flex sm:items-center"
            >
              <label className="search-field col-span-2 sm:flex-1">
                <span className="sr-only">Search</span>
                <SearchIcon />
                <input
                  type="search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search questions and answers"
                  className="input-field input-with-icon w-full"
                />
              </label>
              <select
                aria-label="Source"
                value={sourceFile}
                onChange={(e) => {
                  setSourceFile(e.target.value);
                  setPage(1);
                }}
                className="input-field sm:w-44"
              >
                <option value="">All sources</option>
                {sourceFiles.map((file) => (
                  <option key={file} value={file}>
                    {file}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min={1}
                aria-label="Question number"
                placeholder="No."
                value={questionNumber}
                onChange={(e) => setQuestionNumber(e.target.value)}
                className="input-field w-full sm:w-24"
              />
              {filtered && (
                <button type="button" onClick={clearFilters} className="btn-ghost btn-sm col-span-2">
                  Clear
                </button>
              )}
            </form>

            {loadingQuestions && questions.length === 0 ? (
              <div className="glass-card p-10 text-center text-[15px] text-[var(--muted)]">Loading…</div>
            ) : (
              <div
                ref={tableTop}
                className={`flex scroll-mt-20 flex-col gap-3 transition-opacity ${loadingQuestions ? "opacity-60" : ""}`}
              >
                <AdminQuestionTable
                  questions={questions}
                  scrollResetKey={`${page}:${pageSize}`}
                  onView={(question) => setDrawer({ question, mode: "view" })}
                  onEdit={(question) => setDrawer({ question, mode: "edit" })}
                  onDelete={handleDelete}
                />
                <Pagination
                  page={page}
                  pageSize={pageSize}
                  total={totalQuestions}
                  pageSizeOptions={PAGE_SIZES}
                  disabled={loadingQuestions}
                  onPageChange={goToPage}
                  onPageSizeChange={changePageSize}
                />
              </div>
            )}
          </>
        )}

        {tab === "users" && <AdminUserPanel />}
        {tab === "tasks" && <AdminTaskPanel />}
      </div>

      {drawer && (
        <QuestionDrawer
          question={drawer.question}
          mode={drawer.mode}
          onModeChange={(mode) => setDrawer({ ...drawer, mode })}
          onClose={() => setDrawer(null)}
          onSaved={(question) => {
            setDrawer({ question, mode: "view" });
            void loadQuestions();
          }}
        />
      )}
    </AdminShell>
  );
}

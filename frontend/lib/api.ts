const CONFIGURED_API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

function apiBaseUrl() {
  // Browser requests always go through the Next.js origin. This keeps auth
  // cookies and API calls on one host and works identically from the
  // development computer and phones on the local network.
  return typeof window === "undefined" ? CONFIGURED_API_BASE_URL : "";
}

export type Role = "admin" | "user";

export type Task = {
  id: string;
  name: string;
  question_count: number;
  source_file: string | null;
  created_at: string;
};

export type AuthUser = {
  id: string;
  username: string; // the login: an email address
  name: string | null;
  role: Role;
  created_at: string;
};

export type QuizQuestion = {
  id: string;
  question_text: string;
  choice_a: string;
  choice_b: string;
  choice_c: string;
  choice_d: string;
};

export type AdminQuestion = QuizQuestion & {
  source_file: string;
  source_page: number | null;
  question_number: number;
  correct_answer: "A" | "B" | "C" | "D";
  is_active: boolean;
  needs_review: boolean;
};

export type AdminQuestionPage = {
  items: AdminQuestion[];
  total: number;
};

export type SubmitResult = {
  score: number;
  total: number;
  attempt_id?: string | null;
  submitted_at?: string | null;
  per_question_results: {
    question_id: string;
    selected_answer: string;
    correct_answer: string;
    is_correct: boolean;
  }[];
};

export type QuizAttempt = {
  id: string;
  task_id: string | null; // null for a quick quiz
  task_name: string;
  score: number;
  total: number;
  submitted_at: string;
  per_question_results: (SubmitResult["per_question_results"][number] & {
    question_text: string;
    selected_text: string | null;
    correct_text: string | null;
  })[];
};

// Shows as just the message (String(error) is what the pages display).
class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
  toString() {
    return this.message;
  }
}

async function apiError(res: Response) {
  const body = await res.text();
  let message = `${res.status} ${res.statusText}`;
  try {
    const { detail } = JSON.parse(body);
    if (typeof detail === "string") message = detail;
    else if (Array.isArray(detail)) {
      message = detail.map((d: { msg: string }) => d.msg.replace(/^Value error, /, "")).join("; ");
    }
  } catch {
    // not JSON: keep the status line
  }
  return new ApiError(message, res.status);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${apiBaseUrl()}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!res.ok) throw await apiError(res);
  return res.json();
}

export function login(username: string, password: string) {
  return request<AuthUser>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export function logout() {
  return request<{ status: string }>("/api/auth/logout", { method: "POST" });
}

export function fetchMe() {
  return request<AuthUser>("/api/auth/me");
}

export function fetchAvailableTasks() {
  return request<Task[]>("/api/quiz/tasks");
}

/** Random questions: a task's, or a quick quiz's (count + optional source file). */
export function fetchQuizQuestions(query: { task_id?: string; count?: number; source_file?: string }) {
  const params = new URLSearchParams();
  if (query.task_id) params.set("task_id", query.task_id);
  if (query.count !== undefined) params.set("count", String(query.count));
  if (query.source_file) params.set("source_file", query.source_file);
  return request<QuizQuestion[]>(`/api/quiz/questions?${params.toString()}`);
}

export function fetchQuizSources() {
  return request<string[]>("/api/quiz/source-files");
}

export function submitQuiz(body: {
  task_id?: string; // omitted for a quick quiz
  quiz_name?: string;
  answers: { question_id: string; selected_answer: string }[];
}) {
  return request<SubmitResult>(`/api/quiz/submit`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchQuizHistory() {
  return request<QuizAttempt[]>("/api/quiz/history");
}

export function fetchAdminQuestions(
  filters: {
    source_file?: string;
    question_number?: number;
    include_inactive?: boolean;
    needs_review?: boolean;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}
) {
  const params = new URLSearchParams();
  if (filters.source_file) params.set("source_file", filters.source_file);
  if (filters.question_number !== undefined) params.set("question_number", String(filters.question_number));
  if (filters.include_inactive) params.set("include_inactive", "true");
  if (filters.needs_review !== undefined) params.set("needs_review", String(filters.needs_review));
  if (filters.search) params.set("search", filters.search);
  if (filters.page !== undefined) params.set("page", String(filters.page));
  if (filters.page_size !== undefined) params.set("page_size", String(filters.page_size));
  return request<AdminQuestionPage>(`/api/admin/questions?${params.toString()}`);
}

export type AdminQuestionUpdate = Partial<
  Pick<
    AdminQuestion,
    "question_text" | "choice_a" | "choice_b" | "choice_c" | "choice_d" | "correct_answer" | "needs_review" | "is_active"
  >
>;

export function updateAdminQuestion(id: string, body: AdminQuestionUpdate) {
  return request<AdminQuestion>(`/api/admin/questions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteAdminQuestion(source_file: string, question_number: number) {
  const params = new URLSearchParams({ source_file, question_number: String(question_number) });
  return request<{ status: string }>(`/api/admin/questions?${params.toString()}`, {
    method: "DELETE",
  });
}

export function exportUrl(format: "json" | "csv") {
  return `${apiBaseUrl()}/api/admin/export?format=${format}`;
}

export async function downloadExport(format: "json" | "csv") {
  const res = await fetch(exportUrl(format), { credentials: "include" });
  if (!res.ok) throw new Error(`Export failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = format === "csv" ? "questions_export.csv" : "questions_export.json";
  a.click();
  URL.revokeObjectURL(url);
}

export function fetchSourceFiles() {
  return request<string[]>("/api/admin/source-files");
}

export function fetchTasks() {
  return request<Task[]>("/api/admin/tasks");
}

export function createTask(body: { name: string; question_count: number; source_file?: string | null }) {
  return request<Task>("/api/admin/tasks", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateTask(id: string, body: { name?: string; question_count?: number; source_file?: string | null }) {
  return request<Task>(`/api/admin/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function fetchUsers() {
  return request<AuthUser[]>("/api/admin/users");
}

export function createUser(body: { name: string; username: string; password: string; role: Role }) {
  return request<AuthUser>("/api/admin/users", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateUser(id: string, body: { role: Role }) {
  return request<AuthUser>(`/api/admin/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

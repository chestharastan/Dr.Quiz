const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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
  username: string;
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

export type ImageQuizQuestion = {
  id: string;
  image_path: string;
};

export function imageUrl(imagePath: string) {
  const encoded = imagePath.split("/").map(encodeURIComponent).join("/");
  return `${API_BASE_URL}/static/question_images/${encoded}`;
}

export type QaChoice = {
  label: "A" | "B" | "C" | "D";
  image: string;
};

export type QaQuizQuestion = {
  id: string;
  source_file: string;
  question_number: number;
  question_image: string;
  choices: QaChoice[];
};

export function qaQuestionLabel(q: QaQuizQuestion) {
  const title = q.source_file.replace(/\.md$/i, "");
  return `${title} · Q${String(q.question_number).padStart(4, "0")}`;
}

export function qaImageUrl(imagePath: string) {
  const encoded = imagePath.split("/").map(encodeURIComponent).join("/");
  return `${API_BASE_URL}/static/qa_images/${encoded}`;
}

export type AdminQuestion = QuizQuestion & {
  source_file: string;
  source_page: number;
  question_number: number;
  correct_answer: "A" | "B" | "C" | "D";
  is_active: boolean;
  needs_review: boolean;
  ocr_confidence: number | null;
};

export type SubmitResult = {
  score: number;
  total: number;
  per_question_results: {
    question_id: string;
    selected_answer: string;
    correct_answer: string;
    is_correct: boolean;
  }[];
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
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

export function fetchQuizQuestions(taskId: string) {
  return request<QuizQuestion[]>(`/api/quiz/questions?task_id=${taskId}`);
}

export function submitQuiz(answers: { question_id: string; selected_answer: string }[]) {
  return request<SubmitResult>(`/api/quiz/submit`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export function fetchImageQuestions(count: number) {
  return request<ImageQuizQuestion[]>(`/api/quiz/image-questions?count=${count}`);
}

export function submitImageQuiz(answers: { question_id: string; selected_answer: string }[]) {
  return request<SubmitResult>(`/api/quiz/image-submit`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export function fetchQaQuestions(count: number) {
  return request<QaQuizQuestion[]>(`/api/quiz/qa-questions?count=${count}`);
}

export function submitQaQuiz(answers: { question_id: string; selected_answer: string }[]) {
  return request<SubmitResult>(`/api/quiz/qa-submit`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export function fetchAdminQuestions(
  filters: {
    source_file?: string;
    question_number?: number;
    include_inactive?: boolean;
    needs_review?: boolean;
  } = {}
) {
  const params = new URLSearchParams();
  if (filters.source_file) params.set("source_file", filters.source_file);
  if (filters.question_number !== undefined) params.set("question_number", String(filters.question_number));
  if (filters.include_inactive) params.set("include_inactive", "true");
  if (filters.needs_review !== undefined) params.set("needs_review", String(filters.needs_review));
  return request<AdminQuestion[]>(`/api/admin/questions?${params.toString()}`);
}

export function deleteAdminQuestion(source_file: string, question_number: number) {
  const params = new URLSearchParams({ source_file, question_number: String(question_number) });
  return request<{ status: string }>(`/api/admin/questions?${params.toString()}`, {
    method: "DELETE",
  });
}

export function exportUrl(format: "json" | "csv") {
  return `${API_BASE_URL}/api/admin/export?format=${format}`;
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

export function createUser(body: { username: string; password: string; role: Role }) {
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

import type {
  AnalyticsData,
  AttemptResult,
  ApiPaper,
  CoverageItem,
  DashboardData,
  DbStatus,
  HealthResponse,
  PaperQuestionsResponse,
  QuestionDetail,
  WeaknessesResponse,
} from "./types";

// In production set NEXT_PUBLIC_API_URL to the deployed backend (https://…).
// The localhost default only applies to local development.
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
// Optional API key — must match the backend's API_KEY when one is configured.
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";
const REQUEST_TIMEOUT_MS = 15000;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      headers: { ...headers, ...(options?.headers as Record<string, string>) },
      signal: controller.signal,
      ...options,
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(`API ${res.status} on ${path}:`, text);
      // Surface a generic, status-based message; don't echo server internals.
      throw new Error(`Request failed (${res.status}). Please try again.`);
    }
    return (await res.json()) as T;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Request timed out. Check your connection and retry.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function getDashboard(): Promise<DashboardData> {
  return request<DashboardData>("/api/dashboard");
}

export function getPapers(subject?: string, limit = 500): Promise<ApiPaper[]> {
  const q = new URLSearchParams();
  if (subject) q.set("subject", subject);
  q.set("limit", String(limit));
  return request<ApiPaper[]>(`/api/papers?${q}`);
}

export function getPaperQuestions(paperId: string): Promise<PaperQuestionsResponse> {
  return request<PaperQuestionsResponse>(`/api/papers/${paperId}/questions`);
}

export function getQuestion(questionId: string): Promise<QuestionDetail> {
  return request<QuestionDetail>(`/api/questions/${questionId}`);
}

export function createSession(body: {
  paper_id: number;
  official_time_seconds: number;
  target_time_seconds: number;
}): Promise<{ session_id: number }> {
  return request<{ session_id: number }>("/api/sessions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function logQuestionTime(
  sessionId: number,
  questionId: string,
  body: { time_seconds: number; status: "complete" | "skipped" }
): Promise<{ logged: boolean }> {
  return request<{ logged: boolean }>(
    `/api/sessions/${sessionId}/questions/${questionId}`,
    { method: "PATCH", body: JSON.stringify(body) }
  );
}

export function completeSession(
  sessionId: number,
  totalTimeSeconds: number
): Promise<{ completed: boolean; session_id: number }> {
  return request<{ completed: boolean; session_id: number }>(
    `/api/sessions/${sessionId}/complete`,
    { method: "POST", body: JSON.stringify({ total_time_seconds: totalTimeSeconds }) }
  );
}

export function submitAttempt(body: {
  session_id: number | null;
  question_id: number;
  marks_awarded: number;
  marks_available: number;
  mistake_types: string[];
  confidence: number;
  time_seconds: number;
  notes: string;
}): Promise<AttemptResult> {
  return request<AttemptResult>("/api/attempts", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getWeaknesses(): Promise<WeaknessesResponse> {
  return request<WeaknessesResponse>("/api/weaknesses");
}

export function getCoverage(): Promise<CoverageItem[]> {
  return request<CoverageItem[]>("/api/coverage");
}

export function getStatus(): Promise<DbStatus> {
  return request<DbStatus>("/api/status");
}

export function getAnalytics(): Promise<AnalyticsData> {
  return request<AnalyticsData>("/api/analytics");
}

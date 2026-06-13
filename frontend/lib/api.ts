import type {
  AnalyticsData,
  AttemptResult,
  ApiPaper,
  BriefingData,
  CoverageItem,
  DashboardData,
  DbStatus,
  HealthResponse,
  PaperQuestionsResponse,
  QuestionDetail,
  WeaknessesResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    console.error(`API ${res.status} on ${path}:`, text);
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
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

export function getBriefing(): Promise<BriefingData> {
  return request<BriefingData>("/api/briefing");
}

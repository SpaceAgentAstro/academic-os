const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getDashboard: () => request<Record<string, unknown>>("/api/dashboard"),

  getPapers: (subject?: string) =>
    request<unknown[]>(subject ? `/api/papers?subject=${subject}` : "/api/papers"),

  getPaperQuestions: (paperId: string) =>
    request<unknown[]>(`/api/papers/${paperId}/questions`),

  getQuestion: (questionId: string) =>
    request<unknown>(`/api/questions/${questionId}`),

  createSession: (body: { paper_id: string; target_seconds: number }) =>
    request<{ id: string }>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // Used during timer: logs time only
  logQuestionTime: (
    sessionId: string,
    questionId: string,
    body: { time_seconds: number; status?: string }
  ) =>
    request<{ ok: boolean }>(`/api/sessions/${sessionId}/questions/${questionId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  // Used during marking: saves marks (and optionally time)
  markQuestion: (
    sessionId: string,
    questionId: string,
    body: { awarded: number; tags: string[]; confidence: number; note?: string; time_seconds?: number }
  ) =>
    request<{ ok: boolean; outcome: string; score_pct: number | null }>(
      `/api/sessions/${sessionId}/questions/${questionId}`,
      { method: "PATCH", body: JSON.stringify(body) }
    ),

  completeSession: (sessionId: string) =>
    request<{ ok: boolean }>(`/api/sessions/${sessionId}/complete`, { method: "POST" }),

  getSessionSummary: (sessionId: string) =>
    request<unknown>(`/api/sessions/${sessionId}/summary`),

  logAttempt: (body: {
    session_id?: string;
    question_id: string;
    awarded: number;
    max_marks: number;
    confidence: number;
    tags: string[];
    time_seconds: number;
  }) =>
    request<unknown>("/api/attempts", { method: "POST", body: JSON.stringify(body) }),
};

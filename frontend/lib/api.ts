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

  getPapers: () => request<unknown[]>("/api/papers"),

  getPaperQuestions: (paperId: string) =>
    request<unknown[]>(`/api/papers/${paperId}/questions`),

  getQuestion: (questionId: string) =>
    request<unknown>(`/api/questions/${questionId}`),

  createSession: (body: { paper_id: string; target_seconds: number }) =>
    request<{ id: string }>("/api/sessions", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  markQuestion: (
    sessionId: string,
    questionId: string,
    body: { awarded: number; tags: string[]; confidence: number; note?: string }
  ) =>
    request<unknown>(`/api/sessions/${sessionId}/questions/${questionId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  completeSession: (sessionId: string) =>
    request<unknown>(`/api/sessions/${sessionId}/complete`, { method: "POST" }),

  logAttempt: (body: {
    question_id: string;
    awarded: number;
    max_marks: number;
    confidence: number;
    tags: string[];
    time_seconds: number;
  }) =>
    request<unknown>("/api/attempts", { method: "POST", body: JSON.stringify(body) }),
};

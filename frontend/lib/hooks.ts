"use client";

import { useState, useEffect, useCallback } from "react";
import type { ApiPaper, ApiQuestion, DashboardData } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Generic hook — fetches once on mount (or when dep changes)
// ---------------------------------------------------------------------------

export function useApi<T>(
  endpoint: string | null,
  fallback: T,
  isUsable: (d: T) => boolean = (d) =>
    Array.isArray(d) ? (d as unknown[]).length > 0 : Boolean(d),
): { data: T; loading: boolean; error: string | null } {
  const [data, setData] = useState<T>(fallback);
  const [loading, setLoading] = useState(endpoint !== null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!endpoint) return;
    setLoading(true);
    setError(null);
    const controller = new AbortController();
    fetch(`${API}${endpoint}`, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`API ${r.status}`);
        return r.json() as Promise<T>;
      })
      .then((d: T) => {
        if (isUsable(d)) setData(d);
        else setData(fallback);
        setLoading(false);
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setError(e.message ?? "Request failed");
          console.error(`[api] ${endpoint}:`, e);
        }
        setLoading(false);
      });
    return () => controller.abort();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint]);

  return { data, loading, error };
}

// ---------------------------------------------------------------------------
// Polling hook — refetches every intervalMs
// ---------------------------------------------------------------------------

export function usePolling<T>(
  endpoint: string | null,
  fallback: T,
  intervalMs: number = 60000,
): { data: T; loading: boolean; error: string | null } {
  const [data, setData] = useState<T>(fallback);
  const [loading, setLoading] = useState(endpoint !== null);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = useCallback(() => {
    if (!endpoint) return;
    fetch(`${API}${endpoint}`)
      .then((r) => (r.ok ? r.json() as Promise<T> : Promise.reject(new Error(`API ${r.status}`))))
      .then((d: T) => { setData(d); setLoading(false); setError(null); })
      .catch((e) => { setError(e.message ?? "Failed"); setLoading(false); });
  }, [endpoint]);

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, intervalMs);
    return () => clearInterval(id);
  }, [fetch_, intervalMs]);

  return { data, loading, error };
}

// ---------------------------------------------------------------------------
// Dashboard (polls every 60s)
// ---------------------------------------------------------------------------

const EMPTY_DASHBOARD: DashboardData = {
  metrics: { total_questions_attempted: 0, avg_score: 0, sessions: 0 },
  due_reviews: [],
  examiner_traps: [],
  question_of_day: null,
};

export function useDashboard() {
  return usePolling<DashboardData>("/api/dashboard", EMPTY_DASHBOARD, 60000);
}

// ---------------------------------------------------------------------------
// DB status (Settings screen)
// ---------------------------------------------------------------------------

export interface DbEntry {
  name: string;
  label: string;
  ok: boolean;
}

export interface DbStatus {
  databases: DbEntry[];
}

export function useStatus(): { data: DbStatus | null; loading: boolean } {
  const { data, loading } = useApi<DbStatus | null>(
    "/api/status",
    null,
    (d) => Boolean(d?.databases?.length),
  );
  return { data, loading };
}

// ---------------------------------------------------------------------------
// Raw papers from question_bank.db
// ---------------------------------------------------------------------------

export type RawPaper = ApiPaper;

export function useRawPapers(subject?: string): { data: RawPaper[]; loading: boolean } {
  const ep = subject ? `/api/papers?subject=${subject}` : "/api/papers";
  const { data, loading } = useApi<RawPaper[]>(ep, [], (d) => Array.isArray(d) && d.length > 0);
  return { data, loading };
}

// ---------------------------------------------------------------------------
// Questions for a paper
// ---------------------------------------------------------------------------

export function usePaperQuestions(paperId: string | null): {
  data: ApiQuestion[];
  loading: boolean;
  error: string | null;
} {
  const ep = paperId ? `/api/papers/${paperId}/questions` : null;
  const { data, loading, error } = useApi<ApiQuestion[]>(ep, [], (d) => Array.isArray(d));
  return { data, loading, error };
}

// ---------------------------------------------------------------------------
// Single question with markscheme
// ---------------------------------------------------------------------------

export function useQuestion(questionId: string | null): {
  data: ApiQuestion | null;
  loading: boolean;
} {
  const ep = questionId ? `/api/questions/${questionId}` : null;
  const { data, loading } = useApi<ApiQuestion | null>(ep, null, (d) => d !== null);
  return { data, loading };
}

// ---------------------------------------------------------------------------
// Coverage (question counts per subject)
// ---------------------------------------------------------------------------

export interface CoverageItem {
  subject: string;
  subject_id: string;
  papers: number;
  total_questions: number;
  attempted: number;
  pct: number;
}

export function useCoverage(): CoverageItem[] {
  const { data } = useApi<CoverageItem[]>(
    "/api/coverage",
    [],
    (d) => Array.isArray(d) && d.length > 0,
  );
  return data;
}

// ---------------------------------------------------------------------------
// Subject detail
// ---------------------------------------------------------------------------

export interface SubjectUnit {
  code: string;
  name: string;
  mastery: number;
  spec_points: number;
  questions: number;
  papers: number;
  confidence: number;
}

export interface SubjectAttempt {
  id: string;
  unit: string;
  started_at: string;
  score: number | null;
  max: number | null;
  pct: number;
  minutes: number;
}

export interface SubjectDetail {
  subject: string;
  name: string;
  units: SubjectUnit[];
  recent_attempts: SubjectAttempt[];
  totals: { papers: number; questions: number; sessions: number };
}

const EMPTY_SUBJECT: SubjectDetail = {
  subject: "",
  name: "",
  units: [],
  recent_attempts: [],
  totals: { papers: 0, questions: 0, sessions: 0 },
};

export function useSubject(subject: string | null): { data: SubjectDetail; loading: boolean } {
  const ep = subject ? `/api/subjects/${subject}` : null;
  const { data, loading } = useApi<SubjectDetail>(ep, EMPTY_SUBJECT, (d) => Boolean(d?.name));
  return { data, loading };
}

// ---------------------------------------------------------------------------
// Weaknesses
// ---------------------------------------------------------------------------

export interface WeaknessItem {
  subject: string;
  unit: string;
  topic: string;
  subtopic: string;
  attempts: number;
  avg: number;
  lost: number;
  primary: string;
  secondary: string;
  trap: boolean;
  trend: "up" | "down" | "flat" | string;
  breakdown: { tag: string; n: number }[];
}

export function useWeaknesses(): { data: WeaknessItem[]; loading: boolean } {
  const { data, loading } = useApi<WeaknessItem[]>(
    "/api/weaknesses",
    [],
    () => true,
  );
  return { data, loading };
}

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

export interface AnalyticsData {
  score_trend: number[];
  sessions: number;
}

export function useAnalytics(): { data: AnalyticsData; loading: boolean } {
  const { data, loading } = useApi<AnalyticsData>(
    "/api/analytics",
    { score_trend: [], sessions: 0 },
    () => true,
  );
  return { data, loading };
}

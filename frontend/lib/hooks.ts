"use client";

import { useState, useEffect } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Core hook — starts with fallback, replaces with live data if response is non-empty
// ---------------------------------------------------------------------------

export function useApi<T>(
  endpoint: string,
  fallback: T,
  isUsable: (d: T) => boolean = (d) =>
    Array.isArray(d) ? (d as unknown[]).length > 0 : Boolean(d),
): T {
  const [data, setData] = useState<T>(fallback);

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API}${endpoint}`, { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((d: T | null) => {
        if (d !== null && d !== undefined && isUsable(d)) setData(d);
      })
      .catch(() => {});
    return () => controller.abort();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [endpoint]);

  return data;
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

export function useStatus(): DbStatus | null {
  return useApi<DbStatus | null>(
    "/api/status",
    null,
    (d) => Boolean(d?.databases?.length),
  );
}

// ---------------------------------------------------------------------------
// Raw papers from question_bank.db (Analytics screen)
// ---------------------------------------------------------------------------

export interface RawPaper {
  id: string;
  code: string;
  full_code: string;
  subject: string;
  unit: string;
  session: string;
  year: number;
  question_count: number;
  score: null;
  max: null;
  time: null;
  target: null;
  days_ago: null;
}

export function useRawPapers(subject?: string): RawPaper[] {
  const ep = subject ? `/api/papers?subject=${subject}` : "/api/papers";
  return useApi<RawPaper[]>(ep, [], (d) => Array.isArray(d) && d.length > 0);
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
  return useApi<CoverageItem[]>(
    "/api/coverage",
    [],
    (d) => Array.isArray(d) && d.length > 0,
  );
}

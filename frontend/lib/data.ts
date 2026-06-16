import type { Grade, MasteryBand } from "./types";

// Pure display helpers only. All data comes from the API (lib/api.ts) —
// nothing in this file may contain student data, scores, or content.

export function gradeFromPct(p: number): Grade {
  if (p >= 90) return "A*";
  if (p >= 80) return "A";
  if (p >= 70) return "B";
  if (p >= 60) return "C";
  if (p >= 50) return "D";
  return "E";
}

export function masteryBand(m: number): MasteryBand {
  return m >= 80 ? "green" : m >= 50 ? "amber" : "red";
}

export function bandColor(band: MasteryBand): string {
  return band === "green" ? "var(--accent)" : band === "amber" ? "var(--warn)" : "var(--danger)";
}

// Static reference labels for the five enrolled subjects (display names, not data)
export const SUBJECT_LABELS: Record<string, { name: string; short: string; board: string }> = {
  physics:   { name: "Physics",          short: "PHY", board: "Pearson Edexcel IAL" },
  maths:     { name: "Mathematics",      short: "MAT", board: "Pearson Edexcel IAL" },
  fmaths:    { name: "Further Maths",    short: "FM",  board: "Pearson Edexcel IAL" },
  chemistry: { name: "Chemistry",        short: "CHM", board: "Pearson Edexcel IAL" },
  cs:        { name: "Computer Science", short: "CS",  board: "Cambridge International" },
};

export function subjectName(id: string): string {
  return SUBJECT_LABELS[id]?.name ?? id;
}

export function greeting(d: Date = new Date()): string {
  const h = d.getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

export function todayStr(): string {
  return new Date().toLocaleDateString("en-GB", {
    weekday: "short", day: "numeric", month: "short", year: "numeric",
  });
}

export function fmtClock(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

export function fmtMmss(s: number): string {
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

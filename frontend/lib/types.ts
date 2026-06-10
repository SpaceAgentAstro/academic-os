export type MasteryBand = "green" | "amber" | "red";
export type BadgeTone = "neutral" | "primary" | "green" | "amber" | "red" | "due";
export type Grade = "A*" | "A" | "B" | "C" | "D" | "E";

export interface Topic {
  name: string;
  mastery: number;
  q: number;
  trap?: boolean;
}

export interface Unit {
  code: string;
  name: string;
  mastery: number;
  questions: number;
  topics: Topic[];
}

export interface Subject {
  id: string;
  name: string;
  board: string;
  short: string;
  current: Grade;
  predicted: Grade;
  confidence: number;
  papers: number;
  questions: number;
  avg: number;
  units: Unit[];
}

export interface Paper {
  id: string;
  code: string;
  subject: string;
  unit: string;
  session: string;
  score: number;
  max: number;
  time: number;
  target: number;
  daysAgo: number;
}

export interface MarkschemeEntry {
  code: string;
  text: string;
}

export interface Question {
  n: number;
  part: string;
  marks: number;
  topic: string;
  sub: string;
  text: string;
  scheme: MarkschemeEntry[];
  examiner: string | null;
  awarded: number | null;
}

export interface MarkingPaper {
  code: string;
  session: string;
  unit: string;
  max: number;
  questions: Question[];
}

export interface Weakness {
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
  trend: "up" | "down" | "flat";
  breakdown: { tag: string; n: number }[];
}

export interface ConfidenceTrap {
  text: string;
  topic: string;
  conf: number;
  score: number;
}

export interface ExaminerTrap {
  topic: string;
  text: string;
  years: string[];
  freq: number;
}

export interface ReviewStep {
  label: string;
  ok: boolean;
  note?: string;
}

export interface ReviewQuestion {
  id: string;
  paper: string;
  topic: string;
  marks: number;
  yourScore: number;
  confidence: number;
  time: string;
  text: string;
  steps: ReviewStep[];
  markscheme: MarkschemeEntry[];
  examiner: string;
  similar: { id: string; label: string }[];
}

export interface University {
  name: string;
  course: string;
  req: string;
  reqGrades: Grade[];
  current: Grade[];
  readiness: number;
  predicted: number;
  confidence: "High" | "Medium" | "Low";
  trend: "up" | "down" | "flat";
  risks: string[];
}

export interface DueReview {
  topic: string;
  subject: string;
  status: string;
  overdue: boolean;
}

export interface TodayPriority {
  topic: string;
  reason: string;
  difficulty: "high" | "med" | "low";
  subject: string;
}

export interface Coverage {
  subject: string;
  attempted: number;
  pct: number;
}

export interface BookletDefinition {
  term: string;
  def: string;
  marks: number;
}

export interface BookletFormula {
  eq: string;
  vars: string;
}

export interface Booklet {
  topic: string;
  subject: string;
  unit: string;
  theory: string[];
  definitions: BookletDefinition[];
  formulae: BookletFormula[];
  worked: { q: string; steps: string[] };
  pastQuestions: { year: string; paper: string; marks: number; difficulty: string }[];
  mistakes: string[];
  advice: string[];
  ladder: { label: string; level: number }[];
}

export interface CalibrationPoint {
  conf: number;
  score: number;
}

export interface Requirement {
  subject: string;
  required: Grade;
  current: Grade;
  predicted: Grade;
  status: "exceed" | "track" | "risk";
}

export type Route =
  | "home"
  | "briefing"
  | "timer"
  | "marking"
  | "subjects"
  | "questions"
  | "tutor"
  | "booklets"
  | "analytics"
  | "weaknesses"
  | "university"
  | "settings";

// ── API response types (real data from backend) ──────────────────────────────

export interface ApiPaper {
  id: string;
  code: string;
  full_code: string;
  subject: string;
  unit: string;
  session: string;
  year: number;
  question_count: number;
  score: number | null;
  max: number | null;
  time: number | null;
  target: number | null;
  days_ago: number | null;
}

export interface ApiQuestion {
  id: string;
  n: string;
  marks: number;
  text: string;
  latex: string;
  difficulty: number;
  has_diagram: boolean;
  paper_code: string;
  session: string;
  subject: string;
  module_code: string;
  markscheme: { code: string; text: string }[];
  examiner: string | null;
}

export interface DashboardMetrics {
  total_questions_attempted: number;
  avg_score: number;
  sessions: number;
}

export interface DashboardData {
  metrics: DashboardMetrics;
  due_reviews: { topic: string; subject: string; status: string; overdue: boolean }[];
  examiner_traps: { topic: string; text: string; years: string[]; freq: number }[];
  question_of_day: {
    id: string;
    topic: string;
    unit: string;
    marks: number;
    difficulty: string;
    text: string;
  } | null;
}

export interface SessionParams {
  paperId?: string;
  sessionId?: string;
  paperCode?: string;
  paperUnit?: string;
  paperSession?: string;
}

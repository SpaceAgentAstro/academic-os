export type MasteryBand = "green" | "amber" | "red";
export type BadgeTone = "neutral" | "primary" | "green" | "amber" | "red" | "due";
export type Grade = "A*" | "A" | "B" | "C" | "D" | "E" | "U";

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

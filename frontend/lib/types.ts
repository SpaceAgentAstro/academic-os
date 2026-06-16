export type MasteryBand = "green" | "amber" | "red";
export type BadgeTone = "neutral" | "primary" | "green" | "amber" | "red" | "due";
export type Grade = "A*" | "A" | "B" | "C" | "D" | "E" | "U";

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

// ---------------------------------------------------------------------------
// API response types — one per endpoint, mirroring backend/main.py exactly
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  databases: {
    question_bank: { questions: number; papers: number };
    markscheme: { points: number };
    examiner_reports: { observations: number };
    progress: { topics: number; due_today: number };
    attempts: { total: number; sessions: number };
  };
  briefing_ready: boolean;
  timestamp: string;
}

export interface ApiPaper {
  id: string;
  code: string;
  full_code: string;
  subject: string;
  unit: string;
  session: string;
  year: number;
  question_count: number;
  total_marks: number;
  score: number | null;
  max: number | null;
  time: number | null;
  target: number | null;
  days_ago: number | null;
}

export interface MarkschemePoint {
  code: string;
  mark_type: string;
  marks_value: number;
  text: string;
  sequence?: number;
  conditionality: string | null;
}

export interface ApiQuestion {
  id: string;
  question_number: string;
  question_text: string | null;
  marks: number;
  difficulty: number;
  has_diagram: number;
  command_word: string | null;
  topic: string | null;
  subtopic: string | null;
  markscheme: MarkschemePoint[];
}

export interface PaperQuestionsResponse {
  paper: {
    id: string;
    code: string;
    full_code: string;
    subject: string;
    unit: string;
    session: string;
    year: number;
    total_marks: number;
  };
  questions: ApiQuestion[];
}

export interface ExaminerObservation {
  description: string;
  observation_type: string;
  emphasis_level: number;
}

export interface PreviousAttempt {
  id: number;
  marks_awarded: number;
  marks_available: number;
  confidence: number | null;
  time_seconds: number;
  notes: string | null;
  created_at: string;
  mistakes: string[];
}

export interface QuestionDetail {
  id: string;
  question_number: string;
  question_text: string | null;
  marks: number;
  difficulty: number;
  has_diagram: number;
  command_word: string | null;
  paper: {
    id: string;
    code: string;
    subject: string;
    unit: string;
    session: string;
    year: number;
  };
  topic: string | null;
  topics: { topic: string; subtopic: string | null; is_primary: number }[];
  markscheme: MarkschemePoint[];
  examiner_observations: ExaminerObservation[];
  misconceptions: { description: string; topic: string; frequency: number }[];
  similar_questions: { id: string; label: string }[];
  previous_attempts: PreviousAttempt[];
}

export interface TodaysPriority {
  topic: string;
  subtopic: string | null;
  unit: string;
  subject: string;
  subject_id: string;
  due_date: string;
  mastery: number;
  days_overdue: number;
  primary_mistake: string | null;
}

export interface RecentPaper {
  session_id: number;
  paper_id: string;
  code: string;
  subject: string;
  unit: string;
  session: string;
  score: number | null;
  max: number | null;
  pct: number | null;
  grade: Grade | null;
  time_seconds: number | null;
  target_seconds: number | null;
  started_at: string;
  completed: boolean;
}

export interface UnitMastery {
  code: string;
  mastery: number;
  topic_count: number;
  weak_topics: number;
  questions: number;
  topics: { name: string; mastery: number; reviewed: boolean }[];
}

export interface SubjectMastery {
  subject: string;
  subject_id: string;
  mastery_pct: number;
  topic_count: number;
  reviewed_count: number;
  current_grade: Grade;
  predicted_grade: Grade;
  units: UnitMastery[];
}

export interface PredictedGrade {
  subject: string;
  subject_id: string;
  current: Grade;
  predicted: Grade;
  confidence: "high" | "medium" | "low";
  attempt_count: number;
}

export interface ExaminerTrap {
  text: string;
  topic: string;
  subject: string;
  freq: number;
}

export interface QuestionOfDay {
  id: string;
  topic: string;
  unit: string;
  subject: string;
  marks: number;
  difficulty: string;
  text: string;
  markscheme: { code: string; text: string }[];
}

export interface DashboardData {
  todays_priorities: TodaysPriority[];
  recent_papers: RecentPaper[];
  subject_mastery: SubjectMastery[];
  predicted_grades: PredictedGrade[];
  examiner_traps: ExaminerTrap[];
  question_of_day: QuestionOfDay | null;
  streak: number;
  papers_completed: number;
  average_score: number | null;
  university_readiness: unknown[];
  generated_at: string;
}

export interface Weakness {
  topic: string;
  subtopic: string;
  subject: string;
  unit: string;
  attempts: number;
  avg: number;
  lost: number;
  primary: string;
  secondary: string;
  breakdown: { tag: string; n: number }[];
}

export interface ConfidenceTrap {
  text: string;
  topic: string;
  conf: number;
  score: number;
}

export interface WeaknessesResponse {
  weaknesses: Weakness[];
  confidence_traps: ConfidenceTrap[];
  message: string | null;
}

export interface CoverageItem {
  subject: string;
  subject_id: string;
  papers: number;
  total_questions: number;
  attempted: number;
  pct: number;
}

export interface DbEntry {
  name: string;
  label: string;
  ok: boolean;
}

export interface DbStatus {
  databases: DbEntry[];
}

export interface AnalyticsData {
  score_trend: number[];
  sessions: number;
  calibration: { conf: number; score: number }[];
}

export interface AttemptResult {
  attempt_id: number;
  new_mastery: number | null;
  next_review: string | null;
  marks_awarded: number;
}

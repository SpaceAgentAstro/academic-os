import type {
  Subject, Paper, Weakness, ConfidenceTrap, ExaminerTrap,
  ReviewQuestion, MarkingPaper, University, DueReview,
  TodayPriority, Coverage, Booklet, CalibrationPoint, Requirement, Grade,
} from "./types";

export function gradeFromPct(p: number): Grade {
  if (p >= 90) return "A*";
  if (p >= 80) return "A";
  if (p >= 70) return "B";
  if (p >= 60) return "C";
  if (p >= 50) return "D";
  return "E";
}

export function masteryBand(m: number): "green" | "amber" | "red" {
  return m >= 80 ? "green" : m >= 50 ? "amber" : "red";
}

export function bandColor(band: "green" | "amber" | "red"): string {
  return band === "green" ? "var(--accent)" : band === "amber" ? "var(--warn)" : "var(--danger)";
}

export const subjects: Subject[] = [
  {
    id: "physics", name: "Physics", board: "Pearson Edexcel IAL", short: "PHY",
    current: "A", predicted: "A*", confidence: 84,
    papers: 12, questions: 847, avg: 74,
    units: [
      { code: "U1", name: "Mechanics & Materials", mastery: 81, questions: 168, topics: [
        { name: "Kinematics", mastery: 88, q: 42 },
        { name: "Forces & Newton's laws", mastery: 84, q: 38 },
        { name: "Work, energy & power", mastery: 79, q: 31 },
        { name: "Materials & Young modulus", mastery: 67, q: 29 },
      ]},
      { code: "U2", name: "Waves & Electricity", mastery: 67, questions: 152, topics: [
        { name: "Wave properties", mastery: 74, q: 36 },
        { name: "Refraction & lenses", mastery: 71, q: 28 },
        { name: "DC circuits", mastery: 63, q: 44 },
        { name: "Resistivity", mastery: 58, q: 22 },
      ]},
      { code: "U3", name: "Practical Skills I", mastery: 79, questions: 64, topics: [
        { name: "Uncertainty & errors", mastery: 82, q: 30 },
        { name: "Graphical analysis", mastery: 76, q: 34 },
      ]},
      { code: "U4", name: "Fields & Further Mechanics", mastery: 58, questions: 198, topics: [
        { name: "Momentum & impulse", mastery: 72, q: 41 },
        { name: "Circular motion", mastery: 61, q: 38 },
        { name: "Gravitational fields", mastery: 55, q: 44 },
        { name: "Electric fields", mastery: 49, q: 39 },
        { name: "Magnetic fields", mastery: 52, q: 36 },
      ]},
      { code: "U5", name: "Nuclear, Thermal & Capacitance", mastery: 43, questions: 145, topics: [
        { name: "Capacitance — Discharging", mastery: 31, q: 38, trap: true },
        { name: "Thermal energy", mastery: 47, q: 34 },
        { name: "Nuclear decay", mastery: 44, q: 41 },
        { name: "Oscillations", mastery: 51, q: 32 },
      ]},
      { code: "U6", name: "Practical Skills II", mastery: 72, questions: 60, topics: [
        { name: "Experimental design", mastery: 75, q: 31 },
        { name: "Data evaluation", mastery: 69, q: 29 },
      ]},
    ],
  },
  {
    id: "maths", name: "Mathematics", board: "Pearson Edexcel IAL", short: "MAT",
    current: "A*", predicted: "A*", confidence: 91,
    papers: 9, questions: 312, avg: 82,
    units: [
      { code: "P1", name: "Pure 1", mastery: 88, questions: 72, topics: [
        { name: "Algebra & functions", mastery: 91, q: 30 },
        { name: "Coordinate geometry", mastery: 86, q: 24 },
        { name: "Differentiation", mastery: 87, q: 18 },
      ]},
      { code: "P2", name: "Pure 2", mastery: 84, questions: 68, topics: [
        { name: "Logarithms & exponentials", mastery: 76, q: 26, trap: true },
        { name: "Binomial expansion", mastery: 88, q: 22 },
        { name: "Trigonometry", mastery: 85, q: 20 },
      ]},
      { code: "P3", name: "Pure 3", mastery: 79, questions: 64, topics: [
        { name: "Numerical methods", mastery: 72, q: 20 },
        { name: "Integration", mastery: 81, q: 26 },
        { name: "Vectors", mastery: 83, q: 18 },
      ]},
      { code: "M1", name: "Mechanics 1", mastery: 80, questions: 58, topics: [
        { name: "Kinematics", mastery: 84, q: 30 },
        { name: "Statics", mastery: 76, q: 28 },
      ]},
      { code: "S1", name: "Statistics 1", mastery: 78, questions: 50, topics: [
        { name: "Probability", mastery: 80, q: 26 },
        { name: "Distributions", mastery: 75, q: 24 },
      ]},
    ],
  },
  {
    id: "fmaths", name: "Further Maths", board: "Pearson Edexcel IAL", short: "FM",
    current: "A", predicted: "A*", confidence: 73,
    papers: 5, questions: 89, avg: 68,
    units: [
      { code: "FP1", name: "Further Pure 1", mastery: 74, questions: 30, topics: [
        { name: "Complex numbers", mastery: 78, q: 14 },
        { name: "Matrices", mastery: 70, q: 16 },
      ]},
      { code: "FP2", name: "Further Pure 2", mastery: 52, questions: 28, topics: [
        { name: "Series & method of differences", mastery: 44, q: 14, trap: true },
        { name: "Polar coordinates", mastery: 58, q: 14 },
      ]},
      { code: "FP3", name: "Further Pure 3", mastery: 61, questions: 18, topics: [
        { name: "Hyperbolic functions", mastery: 64, q: 10 },
        { name: "Further integration", mastery: 57, q: 8 },
      ]},
      { code: "FM1", name: "Further Mechanics 1", mastery: 66, questions: 13, topics: [
        { name: "Momentum & collisions", mastery: 66, q: 13 },
      ]},
    ],
  },
  {
    id: "chemistry", name: "Chemistry", board: "Pearson Edexcel IAL", short: "CHM",
    current: "B", predicted: "A", confidence: 69,
    papers: 7, questions: 421, avg: 70,
    units: [
      { code: "U1", name: "Structure, Bonding & Energetics", mastery: 76, questions: 88, topics: [
        { name: "Atomic structure", mastery: 82, q: 30 },
        { name: "Bonding", mastery: 74, q: 30 },
        { name: "Energetics", mastery: 71, q: 28 },
      ]},
      { code: "U2", name: "Energetics & Kinetics", mastery: 68, questions: 80, topics: [
        { name: "Reaction kinetics", mastery: 70, q: 40 },
        { name: "Equilibria", mastery: 66, q: 40, trap: true },
      ]},
      { code: "U4", name: "Rates, Equilibria & Acids", mastery: 64, questions: 96, topics: [
        { name: "Acid–base equilibria", mastery: 60, q: 48, trap: true },
        { name: "Rates of reaction", mastery: 68, q: 48 },
      ]},
      { code: "U5", name: "Transition Metals & Organic", mastery: 58, questions: 90, topics: [
        { name: "Transition metals", mastery: 62, q: 45 },
        { name: "Organic nitrogen", mastery: 54, q: 45 },
      ]},
      { code: "U6", name: "Practical Skills II", mastery: 38, questions: 67, topics: [
        { name: "Titration analysis", mastery: 41, q: 34 },
        { name: "Organic synthesis prep", mastery: 35, q: 33, trap: true },
      ]},
    ],
  },
  {
    id: "cs", name: "Computer Science", board: "Cambridge International", short: "CS",
    current: "A", predicted: "A*", confidence: 80,
    papers: 6, questions: 191, avg: 78,
    units: [
      { code: "P1", name: "Theory Fundamentals", mastery: 83, questions: 70, topics: [
        { name: "Data representation", mastery: 86, q: 24 },
        { name: "Networking", mastery: 80, q: 24 },
        { name: "Processor fundamentals", mastery: 82, q: 22 },
      ]},
      { code: "P2", name: "Algorithms & Programming", mastery: 79, questions: 66, topics: [
        { name: "Algorithm design", mastery: 81, q: 34 },
        { name: "Data structures", mastery: 76, q: 32, trap: true },
      ]},
      { code: "P3", name: "Advanced Theory", mastery: 71, questions: 55, topics: [
        { name: "Boolean algebra", mastery: 74, q: 28 },
        { name: "Recursion", mastery: 68, q: 27, trap: true },
      ]},
    ],
  },
];

export const papers: Paper[] = [
  { id: "WPH14-J24", code: "WPH14", subject: "physics", unit: "U4", session: "June 2024", score: 84, max: 90, time: 74, target: 60, daysAgo: 4 },
  { id: "WMA12-J24", code: "WMA12", subject: "maths", unit: "P2", session: "Jan 2024", score: 71, max: 75, time: 52, target: 50, daysAgo: 8 },
  { id: "WPH13-J23", code: "WPH13", subject: "physics", unit: "U3", session: "June 2023", score: 61, max: 80, time: 88, target: 53, daysAgo: 12 },
  { id: "WCH04-J24", code: "WCH04", subject: "chemistry", unit: "U4", session: "June 2024", score: 58, max: 80, time: 79, target: 53, daysAgo: 16 },
  { id: "WFM01-J23", code: "WFM01", subject: "fmaths", unit: "FP2", session: "June 2023", score: 49, max: 75, time: 71, target: 50, daysAgo: 19 },
  { id: "9618-12", code: "9618/12", subject: "cs", unit: "P1", session: "Oct 2023", score: 58, max: 75, time: 64, target: 60, daysAgo: 23 },
  { id: "WPH11-J23", code: "WPH11", subject: "physics", unit: "U1", session: "June 2023", score: 72, max: 80, time: 66, target: 53, daysAgo: 27 },
  { id: "WMA11-J23", code: "WMA11", subject: "maths", unit: "P1", session: "June 2023", score: 70, max: 75, time: 49, target: 50, daysAgo: 31 },
];

export const scoreTrend: number[] = [58, 61, 57, 64, 60, 66, 63, 69, 67, 71, 68, 73, 70, 76, 72, 78, 75, 80, 79, 84];

export const weaknesses: Weakness[] = [
  { subject: "physics", unit: "U5", topic: "Capacitance", subtopic: "Discharging equations", attempts: 14, avg: 34, lost: 47, primary: "Logarithmic rearrangement", secondary: "Sign errors in exponential expressions", trap: true, trend: "flat", breakdown: [{ tag: "Logarithms", n: 14 }, { tag: "Rearrangement", n: 9 }, { tag: "Units", n: 4 }] },
  { subject: "chemistry", unit: "U6", topic: "Organic synthesis prep", subtopic: "Yield & purification", attempts: 11, avg: 35, lost: 39, primary: "Reagent selection", secondary: "Mechanism arrows", trap: true, trend: "down", breakdown: [{ tag: "Reagents", n: 11 }, { tag: "Mechanism", n: 7 }, { tag: "Conditions", n: 5 }] },
  { subject: "fmaths", unit: "FP2", topic: "Series", subtopic: "Method of differences", attempts: 9, avg: 44, lost: 31, primary: "Telescoping setup", secondary: "Partial fractions", trap: true, trend: "up", breakdown: [{ tag: "Telescoping", n: 9 }, { tag: "Partial fractions", n: 6 }] },
  { subject: "physics", unit: "U4", topic: "Electric fields", subtopic: "Field strength vs potential", attempts: 13, avg: 49, lost: 28, primary: "Wrong method", secondary: "Sign convention", trap: false, trend: "up", breakdown: [{ tag: "Wrong method", n: 8 }, { tag: "Sign error", n: 5 }] },
  { subject: "maths", unit: "P2", topic: "Logarithms", subtopic: "Solving log equations", attempts: 12, avg: 41, lost: 26, primary: "Logarithm laws", secondary: "Domain restrictions", trap: true, trend: "flat", breakdown: [{ tag: "Log laws", n: 9 }, { tag: "Domain", n: 4 }] },
  { subject: "chemistry", unit: "U4", topic: "Acid–base equilibria", subtopic: "pH of buffers", attempts: 10, avg: 52, lost: 22, primary: "Henderson–Hasselbalch", secondary: "Significant figures", trap: false, trend: "up", breakdown: [{ tag: "Buffer eqn", n: 7 }, { tag: "Sig figs", n: 5 }] },
  { subject: "cs", unit: "P3", topic: "Recursion", subtopic: "Tracing recursive calls", attempts: 8, avg: 56, lost: 18, primary: "Base case", secondary: "Stack tracing", trap: false, trend: "flat", breakdown: [{ tag: "Base case", n: 6 }, { tag: "Stack", n: 4 }] },
];

export const confidenceTraps: ConfidenceTrap[] = [
  { text: "Scored 2/6 on capacitor discharge but rated confidence 4", topic: "Capacitance", conf: 4, score: 33 },
  { text: "Scored 3/8 on FP2 series but rated confidence 4", topic: "Series", conf: 4, score: 38 },
  { text: "Scored 2/5 on log equations but rated confidence 5", topic: "Logarithms", conf: 5, score: 40 },
];

export const examinerTraps: ExaminerTrap[] = [
  { topic: "Capacitance", text: "Candidates frequently omit the negative sign in ln(0.25).", years: ["Jun 2023", "Jan 2022", "Jun 2021"], freq: 3 },
  { topic: "Capacitance", text: "Units for capacitance — μF vs F errors common in substitution.", years: ["Jun 2023", "Jan 2020"], freq: 2 },
  { topic: "Further Pure", text: "Proof questions: candidates must show all intermediate steps for method marks.", years: ["Jun 2024", "Jun 2022"], freq: 2 },
  { topic: "Logarithms", text: "Failure to apply natural logarithms correctly when isolating the exponent.", years: ["Jun 2023", "Jun 2021"], freq: 2 },
  { topic: "Electric fields", text: "Confusion between field strength (vector) and potential (scalar).", years: ["Jun 2024"], freq: 1 },
  { topic: "Organic", text: "Mechanism arrows must originate from a bond or lone pair, not an atom.", years: ["Jun 2023", "Jun 2022"], freq: 2 },
];

export const calibration: CalibrationPoint[] = [
  { conf: 1, score: 64 }, { conf: 2, score: 78 }, { conf: 3, score: 70 }, { conf: 4, score: 58 }, { conf: 5, score: 67 },
];

export const questionOfDay = {
  id: "WPH15-Q8b",
  topic: "Capacitance", unit: "Unit 5", marks: 5, difficulty: "Hard",
  text: "A 470 μF capacitor is charged to 12 V and then discharged through a 15 kΩ resistor. Calculate the time taken for the potential difference across the capacitor to fall to 3.0 V.",
};

export const reviewQuestion: ReviewQuestion = {
  id: "WPH14-Q8b", paper: "WPH14 June 2024", topic: "Capacitance", marks: 5,
  yourScore: 2, confidence: 3, time: "4m 12s",
  text: "A 470 μF capacitor, charged to 12 V, discharges through a 15 kΩ resistor. Determine the time for the p.d. to fall to one quarter of its initial value. (5)",
  steps: [
    { label: "Write decay equation V = V₀e^(−t/RC)", ok: true },
    { label: "Substitute values: 3.0 = 12e^(−t/RC)", ok: true },
    { label: "Take natural logarithm of both sides", ok: false, note: "Sign error — dropped the negative" },
    { label: "Rearrange for t", ok: false, note: "Impossible after step 3 failed" },
  ],
  markscheme: [
    { code: "B1", text: "Recognises exponential decay model V = V₀e^(−t/RC)" },
    { code: "M1", text: "Correct substitution of V, V₀ and RC = 7.05 s" },
    { code: "M1", text: "ln(0.25) = −t/RC with correct sign treatment" },
    { code: "A1", text: "t = RC·ln(4) evaluated" },
    { code: "A1", text: "t = 9.8 s (2 s.f.)" },
  ],
  examiner: "June 2024: Most candidates who attempted Q8b failed to apply natural logarithms correctly, dropping the negative sign when isolating t.",
  similar: [
    { id: "WPH14-J22-Q7", label: "Q7 · WPH14 Jun 2022 · 6 marks · RC discharge" },
    { id: "WPH15-J23-Q9", label: "Q9 · WPH15 Jun 2023 · 5 marks · Time constant" },
    { id: "WPH14-J21-Q8", label: "Q8 · WPH14 Jun 2021 · 4 marks · Charging curve" },
  ],
};

export const markingPaper: MarkingPaper = {
  code: "WPH14", session: "June 2024", unit: "Unit 4", max: 80,
  questions: [
    { n: 1, part: "Q1", marks: 5, topic: "Momentum", sub: "Conservation", text: "A trolley of mass 0.80 kg moving at 3.0 m s⁻¹ collides and couples with a stationary 1.20 kg trolley. Calculate the common velocity after collision. (5)", scheme: [{ code: "B1", text: "States conservation of momentum" }, { code: "M1", text: "p_before = 0.80 × 3.0" }, { code: "M1", text: "Equates to (0.80+1.20)v" }, { code: "A1", text: "v = 1.2 m s⁻¹" }, { code: "A1", text: "Correct unit and 2 s.f." }], examiner: null, awarded: 5 },
    { n: 2, part: "Q2", marks: 6, topic: "Circular motion", sub: "Centripetal force", text: "Explain why a car rounding a banked track does not rely solely on friction, and derive the design speed. (6)", scheme: [{ code: "B1", text: "Identifies horizontal component of normal force" }, { code: "M1", text: "Resolves N vertically and horizontally" }, { code: "M1", text: "Sets horizontal component = mv²/r" }, { code: "M1", text: "Eliminates N" }, { code: "A1", text: "v = √(rg tanθ)" }, { code: "A1", text: "Clear logical structure" }], examiner: "Candidates often omit the vertical equilibrium equation.", awarded: 4 },
    { n: 3, part: "Q3", marks: 8, topic: "Gravitational fields", sub: "Orbits", text: "A satellite orbits Earth at radius 7.0 × 10⁶ m. Derive its orbital period and evaluate. (8)", scheme: [{ code: "M1", text: "GMm/r² = mv²/r" }, { code: "M1", text: "v = √(GM/r)" }, { code: "M1", text: "T = 2πr/v" }, { code: "A1", text: "Correct substitution of GM" }, { code: "A1", text: "T ≈ 5.8 × 10³ s" }, { code: "B1", text: "States assumption of circular orbit" }, { code: "B1", text: "Correct units throughout" }, { code: "A1", text: "Answer to 2 s.f." }], examiner: null, awarded: 8 },
    { n: 4, part: "Q4", marks: 4, topic: "Electric fields", sub: "Field strength", text: "Two point charges +2.0 nC and −2.0 nC are 4.0 cm apart. Calculate the field strength at the midpoint. (4)", scheme: [{ code: "M1", text: "E = kQ/r² for one charge" }, { code: "M1", text: "Adds fields (same direction at midpoint)" }, { code: "A1", text: "E = 4.5 × 10⁴ N C⁻¹" }, { code: "A1", text: "States direction toward negative charge" }], examiner: "Field at midpoint of a dipole is additive, not zero — common error.", awarded: 2 },
    { n: 5, part: "Q5", marks: 10, topic: "Capacitance", sub: "Discharging", text: "A 470 μF capacitor charged to 12 V discharges through 15 kΩ. (a) Find the time constant. (b) Find the time for the p.d. to fall to 3.0 V. (c) Sketch the discharge curve. (10)", scheme: [{ code: "B1", text: "τ = RC" }, { code: "A1", text: "τ = 7.05 s" }, { code: "M1", text: "V = V₀e^(−t/RC)" }, { code: "M1", text: "ln(0.25) with correct sign" }, { code: "M1", text: "t = RC ln(4)" }, { code: "A1", text: "t = 9.8 s" }, { code: "B1", text: "Exponential curve through (0, 12)" }, { code: "B1", text: "Correct asymptotic approach to zero" }, { code: "A1", text: "Axes labelled with units" }, { code: "A1", text: "Curve consistent with τ" }], examiner: "June 2024: candidates dropped the negative sign in ln(0.25), losing the M1 and both A1s.", awarded: null },
    { n: 6, part: "Q6", marks: 5, topic: "Magnetic fields", sub: "Force on conductor", text: "A 0.25 m wire carrying 3.0 A sits perpendicular to a 0.40 T field. Find the force. (5)", scheme: [], examiner: null, awarded: null },
    { n: 7, part: "Q7", marks: 6, topic: "Electromagnetic induction", sub: "Faraday's law", text: "A coil of 200 turns and area 1.5 × 10⁻³ m² experiences a flux change. (6)", scheme: [], examiner: null, awarded: null },
    { n: 8, part: "Q8", marks: 4, topic: "Capacitance", sub: "Energy stored", text: "Calculate the energy stored in a 470 μF capacitor at 12 V. (4)", scheme: [], examiner: null, awarded: null },
    { n: 9, part: "Q9", marks: 5, topic: "Circular motion", sub: "Vertical circle", text: "A bucket of water is swung in a vertical circle of radius 1.0 m. Find the minimum speed at the top. (5)", scheme: [], examiner: null, awarded: null },
    { n: 10, part: "Q10", marks: 6, topic: "Gravitational fields", sub: "Potential", text: "Define gravitational potential and calculate it at the surface of Mars. (6)", scheme: [], examiner: null, awarded: null },
    { n: 11, part: "Q11", marks: 4, topic: "Electric fields", sub: "Potential energy", text: "Calculate the work done moving a +5.0 nC charge through a 200 V potential difference. (4)", scheme: [], examiner: null, awarded: null },
    { n: 12, part: "Q12", marks: 5, topic: "Magnetic fields", sub: "Mass spectrometer", text: "An ion of charge +e moves at 2.0 × 10⁵ m s⁻¹ through a 0.30 T field. Find the radius of its path. (5)", scheme: [], examiner: null, awarded: null },
    { n: 13, part: "Q13", marks: 4, topic: "Capacitance", sub: "Combination", text: "Three 100 μF capacitors are connected in series. Find the total capacitance. (4)", scheme: [], examiner: null, awarded: null },
    { n: 14, part: "Q14", marks: 8, topic: "Synoptic", sub: "Fields", text: "Compare gravitational and electric fields, supporting each point with an equation. (8)", scheme: [], examiner: null, awarded: null },
  ],
};

export const markedCount = 7;

export const universities: University[] = [
  { name: "Imperial College London", course: "Physics (MSci)", req: "A*AA", reqGrades: ["A*","A","A"], current: ["A","A*","A"], readiness: 83, predicted: 91, confidence: "High", trend: "up", risks: ["Physics Unit 5 (mastery 43%)", "Chemistry Unit 6 (mastery 38%)", "Time management (118% of target time)"] },
  { name: "UCL", course: "Physics BSc", req: "AAA", reqGrades: ["A","A","A"], current: ["A","A*","A"], readiness: 88, predicted: 93, confidence: "High", trend: "up", risks: ["Physics Unit 5 (mastery 43%)", "Pacing on long-answer questions"] },
  { name: "University of Warwick", course: "Physics & Mathematics (MMathPhys)", req: "A*A*A", reqGrades: ["A*","A*","A"], current: ["A","A*","A"], readiness: 76, predicted: 85, confidence: "Medium", trend: "up", risks: ["Second A* (Physics) not yet secured", "Further Maths FP2 (mastery 52%)", "Chemistry Unit 6 (mastery 38%)"] },
];

export const readinessTimeline = {
  labels: ["Dec","Jan","Feb","Mar","Apr","May","Jun*"],
  values: [62, 66, 71, 74, 79, 83, 91],
};

export const requirements: Requirement[] = [
  { subject: "Physics", required: "A*", current: "A", predicted: "A*", status: "track" },
  { subject: "Mathematics", required: "A", current: "A*", predicted: "A*", status: "exceed" },
  { subject: "Further Maths", required: "A", current: "A", predicted: "A*", status: "exceed" },
  { subject: "Chemistry", required: "A", current: "B", predicted: "A", status: "risk" },
];

export const dueReviews: DueReview[] = [
  { topic: "Capacitance — Discharging", subject: "physics", status: "Overdue 3 days", overdue: true },
  { topic: "FP2 — Series", subject: "fmaths", status: "Due today", overdue: false },
  { topic: "Chemistry Unit 4 — Equilibrium", subject: "chemistry", status: "Due today", overdue: false },
];

export const todaysPriorities: TodayPriority[] = [
  { topic: "Capacitance — Discharging equations", reason: "Due · 3 mistakes", difficulty: "high", subject: "physics" },
  { topic: "Further Maths FP2 — Series", reason: "Not reviewed in 18 days", difficulty: "med", subject: "fmaths" },
  { topic: "Physics Unit 6 — Electromagnetic induction", reason: "Examiner trap", difficulty: "high", subject: "physics" },
];

export const coverage: Coverage[] = [
  { subject: "Physics", attempted: 847, pct: 78 },
  { subject: "Mathematics", attempted: 312, pct: 41 },
  { subject: "Further Maths", attempted: 89, pct: 23 },
  { subject: "Chemistry", attempted: 421, pct: 56 },
  { subject: "Computer Science", attempted: 191, pct: 47 },
];

export const booklet: Booklet = {
  topic: "Capacitance", subject: "Physics", unit: "Unit 5",
  theory: [
    "A capacitor stores energy in the electric field between two conductors separated by a dielectric. The charge stored is proportional to the potential difference across it: Q = CV, where C is the capacitance in farads.",
    "When a charged capacitor discharges through a resistor, the charge, current and voltage all decay exponentially with the same time constant τ = RC. After one time constant the quantity falls to 1/e (≈37%) of its initial value.",
    "Examiners reward candidates who recognise the exponential model immediately and treat the negative sign rigorously when taking natural logarithms — this is the single most common point of mark loss in Unit 5.",
  ],
  definitions: [
    { term: "Capacitance", def: "Charge stored per unit potential difference, C = Q/V.", marks: 1 },
    { term: "Time constant", def: "Product RC; time for charge to fall to 1/e of initial value.", marks: 1 },
    { term: "Dielectric", def: "Insulating material between plates that increases capacitance.", marks: 1 },
  ],
  formulae: [
    { eq: "Q = CV", vars: "Q charge (C), C capacitance (F), V p.d. (V)" },
    { eq: "E = ½CV²", vars: "E energy stored (J)" },
    { eq: "Q = Q₀e^(−t/RC)", vars: "t time (s), R resistance (Ω)" },
    { eq: "τ = RC", vars: "τ time constant (s)" },
  ],
  worked: {
    q: "A 470 μF capacitor charged to 12 V discharges through 15 kΩ. Find the time for the p.d. to fall to 3.0 V.",
    steps: [
      "τ = RC = 15 000 × 470 × 10⁻⁶ = 7.05 s",
      "V = V₀e^(−t/RC) ⟹ 3.0 = 12 e^(−t/7.05)",
      "0.25 = e^(−t/7.05) ⟹ ln(0.25) = −t/7.05",
      "t = −7.05 × ln(0.25) = 7.05 × ln(4) = 9.8 s",
    ],
  },
  pastQuestions: [
    { year: "Jun 2024", paper: "WPH14", marks: 10, difficulty: "Hard" },
    { year: "Jun 2023", paper: "WPH15", marks: 5, difficulty: "Medium" },
    { year: "Jan 2022", paper: "WPH14", marks: 6, difficulty: "Hard" },
    { year: "Jun 2021", paper: "WPH14", marks: 4, difficulty: "Easy" },
    { year: "Jan 2020", paper: "WPH15", marks: 8, difficulty: "Hard" },
  ],
  mistakes: [
    "Dropping the negative sign when taking ln of both sides.",
    "Using μF without converting to farads in substitution.",
    "Confusing time constant τ with half-life.",
  ],
  advice: [
    '“Always quote τ = RC before substituting numbers.” — Jun 2023 report',
    '“Show ln(0.25) = −t/RC explicitly to secure the method mark.” — Jun 2024 report',
  ],
  ladder: [
    { label: "Find τ for given R and C", level: 1 },
    { label: "Charge remaining after one time constant", level: 2 },
    { label: "Time to reach a stated voltage", level: 3 },
    { label: "Energy dissipated during discharge", level: 4 },
    { label: "Two-capacitor network discharge (synoptic)", level: 5 },
  ],
};

export const tutorSeed = [
  { role: "user" as const, text: "Explain why I keep getting the logarithm step wrong." },
  { role: "tutor" as const, text: "Looking at your 14 attempts on capacitor discharge, the breakdown is always at the same point. When Q = Q₀e^(−t/RC), you correctly identify the equation, but when isolating t you write ln(Q/Q₀) = t/RC, dropping the negative sign. The correct form is ln(Q/Q₀) = −t/RC, so t = −RC·ln(Q/Q₀) = RC·ln(Q₀/Q). Flip the ratio and the sign takes care of itself." },
];

export function subjectById(id: string): Subject {
  return subjects.find((s) => s.id === id) ?? subjects[0];
}

export function todayStr(): string {
  return new Date(2026, 5, 8).toLocaleDateString("en-GB", {
    weekday: "short", day: "numeric", month: "short", year: "numeric",
  });
}

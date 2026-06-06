from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

COMMAND_WORDS = frozenset({
    "find", "show that", "prove", "prove that", "show", "state",
    "write down", "calculate", "determine", "evaluate", "sketch",
    "describe", "explain", "suggest", "deduce", "hence", "hence or otherwise",
    "using your answer", "verify", "simplify", "expand", "factorise",
    "differentiate", "integrate", "solve", "given that",
    "obtain", "derive", "express", "complete", "draw",
    "label", "plot", "comment", "compare", "justify",
})

_DIFFICULTY_COMMAND_WEIGHTS: dict[str, int] = {
    "state": 1, "write down": 1,
    "find": 2, "calculate": 2, "solve": 2, "simplify": 2,
    "show that": 3, "prove": 3, "prove that": 3, "differentiate": 2,
    "integrate": 3, "evaluate": 3, "determine": 3,
    "deduce": 4, "hence or otherwise": 4,
    "justify": 4, "derive": 4, "comment": 4,
}

_PROOF_PATTERNS = re.compile(
    r"\b(prove|proof|show that|verify|hence show)\b", re.I
)
_MODELLING_PATTERNS = re.compile(
    r"\b(model|modelling|real[- ]world|context|interpret)\b", re.I
)
_DIAGRAM_PATTERNS = re.compile(
    r"\b(sketch|draw|label|diagram|graph|curve|plot)\b", re.I
)
_MULTI_TOPIC_PATTERNS = re.compile(
    r"\b(hence|using (your|the) (result|answer|expression))\b", re.I
)


def extract_command_word(question_text: str) -> str | None:
    """Identify the command word from question text (longest-match first)."""
    lower = question_text.lower().strip()
    for cw in sorted(COMMAND_WORDS, key=len, reverse=True):
        if lower.startswith(cw) or f"\n{cw}" in lower:
            return cw
    return None


def classify_difficulty(question: dict[str, Any]) -> int:
    """Assign difficulty 1–5 based on marks, command word, and context.

    Scale:
      1 — Recall / definition
      2 — Standard single-step
      3 — Multi-step application
      4 — Advanced synthesis
      5 — Examiner-trap / proof under pressure
    """
    marks: int = question.get("marks", 0)
    command_word: str | None = question.get("command_word")
    text: str = question.get("raw_text", "")

    # Base from command word weight
    if command_word:
        cw_score = _DIFFICULTY_COMMAND_WEIGHTS.get(command_word.lower(), 2)
    else:
        cw_score = 2

    # Adjust for marks
    if marks <= 2:
        marks_score = 1
    elif marks <= 4:
        marks_score = 2
    elif marks <= 6:
        marks_score = 3
    elif marks <= 9:
        marks_score = 4
    else:
        marks_score = 5

    # Examiner-trap signals: prove/show with high marks
    if _PROOF_PATTERNS.search(text) and marks >= 5:
        return 5

    difficulty = round((cw_score + marks_score) / 2)
    return max(1, min(5, difficulty))


def classify_tags(question: dict[str, Any]) -> list[str]:
    """Assign question tags from the allowed set.

    Allowed: Proof, Modelling, Calculation, Interpretation, Evaluation,
             Data Analysis, Diagram Based, Multi Topic.
    """
    text: str = question.get("raw_text", "")
    tags: list[str] = []

    if _PROOF_PATTERNS.search(text):
        tags.append("Proof")
    if _MODELLING_PATTERNS.search(text):
        tags.append("Modelling")
    if _DIAGRAM_PATTERNS.search(text):
        tags.append("Diagram Based")
    if _MULTI_TOPIC_PATTERNS.search(text):
        tags.append("Multi Topic")

    # Calculation — default if no other specific tag
    has_calc = re.search(r"\b(calculate|find|solve|evaluate|simplify)\b", text, re.I)
    if has_calc and "Proof" not in tags:
        tags.append("Calculation")

    if re.search(r"\b(interpret|comment|explain|describe)\b", text, re.I):
        tags.append("Interpretation")

    if re.search(r"\b(evaluate|compare|assess)\b", text, re.I):
        tags.append("Evaluation")

    if re.search(r"\b(table|data|given.{0,20}values?|read.{0,20}graph)\b", text, re.I):
        tags.append("Data Analysis")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_tags: list[str] = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)

    return unique_tags


# ── Topic classification ─────────────────────────────────────────────────────
# Keyword → (topic, subtopic) mapping per subject domain.
# These are heuristic — the Curriculum Agent validates against spec points.

_MATHS_TOPIC_KEYWORDS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(differentiat|gradient|tangent|normal|rate of change)", re.I), "Calculus", "Differentiation"),
    (re.compile(r"\b(integrat|area under|volume of revolution)", re.I), "Calculus", "Integration"),
    (re.compile(r"\b(binomial|expansion|coefficient|Pascal)\b", re.I), "Algebra", "Binomial Theorem"),
    (re.compile(r"\b(logarithm|ln|log|exponential|e\^)\b", re.I), "Algebra", "Exponentials and Logarithms"),
    (re.compile(r"\b(trigonometr|sin|cos|tan|CAST|identit)\b", re.I), "Trigonometry", "Trigonometric Functions"),
    (re.compile(r"\b(vector|scalar|magnitude|direction)\b", re.I), "Vectors", "Vector Geometry"),
    (re.compile(r"\b(sequence|series|arithmetic|geometric|sum to infinity)\b", re.I), "Sequences", "Series"),
    (re.compile(r"\b(proof by|contradiction|induction)\b", re.I), "Proof", "Mathematical Proof"),
    (re.compile(r"\b(statistic|probability|normal distribution|binomial dist|hypothesis)\b", re.I), "Statistics", "Statistical Methods"),
    (re.compile(r"\b(mechanics|velocity|acceleration|force|Newton|projectile)\b", re.I), "Mechanics", "Kinematics"),
    (re.compile(r"\b(complex number|Argand|modulus argument|locus)\b", re.I), "Further Pure", "Complex Numbers"),
    (re.compile(r"\b(matrix|matrices|determinant|inverse|eigenvalue)\b", re.I), "Further Pure", "Matrices"),
    (re.compile(r"\b(hyperbolic|sinh|cosh|tanh)\b", re.I), "Further Pure", "Hyperbolic Functions"),
]

_PHYSICS_TOPIC_KEYWORDS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(electric field|capacitor|capacitance|charge)\b", re.I), "Electricity", "Electric Fields"),
    (re.compile(r"\b(wave|frequency|wavelength|diffraction|interference)\b", re.I), "Waves", "Wave Behaviour"),
    (re.compile(r"\b(quantum|photon|photoelectric|de Broglie)\b", re.I), "Quantum Physics", "Quantum Phenomena"),
    (re.compile(r"\b(nuclear|radioactive|decay|half.life|fission|fusion)\b", re.I), "Nuclear Physics", "Nuclear Decay"),
    (re.compile(r"\b(magnetic|flux|induction|Faraday|Lenz)\b", re.I), "Electromagnetism", "Magnetic Fields"),
    (re.compile(r"\b(momentum|kinetic|potential|work|energy|power)\b", re.I), "Mechanics", "Energy and Power"),
    (re.compile(r"\b(circular motion|centripetal|angular)\b", re.I), "Mechanics", "Circular Motion"),
    (re.compile(r"\b(gravitational field|orbital|satellite|Kepler)\b", re.I), "Gravity", "Gravitational Fields"),
    (re.compile(r"\b(thermal|temperature|gas law|ideal gas|Boltzmann)\b", re.I), "Thermal Physics", "Thermal Properties"),
]

_CHEMISTRY_TOPIC_KEYWORDS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(enthalpy|Hess|bond energy|lattice)\b", re.I), "Energetics", "Enthalpy Changes"),
    (re.compile(r"\b(equilibrium|Kc|Kp|Le Chatelier)\b", re.I), "Equilibrium", "Dynamic Equilibrium"),
    (re.compile(r"\b(acid|base|pH|buffer|neutralis)\b", re.I), "Acid-Base Chemistry", "Acids and Bases"),
    (re.compile(r"\b(electrode|electrolysis|redox|oxidation state)\b", re.I), "Electrochemistry", "Redox Reactions"),
    (re.compile(r"\b(rate|order|half.life|activation energy|catalyst)\b", re.I), "Kinetics", "Reaction Rates"),
    (re.compile(r"\b(organic|alkane|alkene|alcohol|ester|aldehyde|ketone)\b", re.I), "Organic Chemistry", "Organic Functional Groups"),
    (re.compile(r"\b(periodic table|trend|ionisation|atomic radius)\b", re.I), "Periodicity", "Periodic Trends"),
    (re.compile(r"\b(NMR|spectroscopy|infrared|mass spec)\b", re.I), "Analytical Chemistry", "Spectroscopy"),
]

_CS_TOPIC_KEYWORDS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"\b(algorithm|sort|search|complexity|O\(n\))\b", re.I), "Algorithms", "Algorithmic Thinking"),
    (re.compile(r"\b(data structure|stack|queue|linked list|tree|graph)\b", re.I), "Data Structures", "Abstract Data Types"),
    (re.compile(r"\b(network|TCP|IP|protocol|OSI|router)\b", re.I), "Networking", "Network Protocols"),
    (re.compile(r"\b(database|SQL|relational|normalisation|entity)\b", re.I), "Databases", "Relational Databases"),
    (re.compile(r"\b(programming|OOP|class|object|inheritance|polymorphism)\b", re.I), "Programming", "Object-Oriented Programming"),
    (re.compile(r"\b(security|encrypt|decrypt|cipher|hash|RSA)\b", re.I), "Security", "Cryptography"),
    (re.compile(r"\b(boolean|logic gate|flip.flop|circuit)\b", re.I), "Logic", "Boolean Logic"),
    (re.compile(r"\b(operating system|process|thread|memory management)\b", re.I), "Systems", "Operating Systems"),
]

_SUBJECT_KEYWORD_MAPS: dict[str, list[tuple[re.Pattern, str, str]]] = {
    "mathematics": _MATHS_TOPIC_KEYWORDS,
    "further mathematics": _MATHS_TOPIC_KEYWORDS,
    "physics": _PHYSICS_TOPIC_KEYWORDS,
    "chemistry": _CHEMISTRY_TOPIC_KEYWORDS,
    "computer science": _CS_TOPIC_KEYWORDS,
}


def classify_topic(
    question: dict[str, Any],
    subject: str,
    module_code: str,
) -> tuple[str, str]:
    """Return (topic, subtopic) for a question using keyword heuristics.

    Falls back to (module_code, "General") if no keyword matches.
    The Curriculum Agent may refine this against actual spec points.
    """
    text: str = question.get("raw_text", "")
    keyword_map = _SUBJECT_KEYWORD_MAPS.get(subject.lower(), [])
    for pattern, topic, subtopic in keyword_map:
        if pattern.search(text):
            return topic, subtopic
    return module_code, "General"

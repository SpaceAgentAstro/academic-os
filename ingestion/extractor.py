from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Matches Edexcel IAL question paper numbering: "1.", "2)", "Q1", "Question 1."
_QUESTION_START = re.compile(
    r"(?m)^(?:"
    r"Question\s+(\d{1,2})\s*[.):]?\s*$"  # "Question 1" (end of line) or "Question 1:"
    r"|(?:Question\s+)?(\d{1,2})\s*[.)](?!\d)"  # "1." or "Question 1." (not decimal like 0.1)
    r"|Q(\d{1,2})\b"                        # "Q1"
    r")",
    re.IGNORECASE,
)

# Mark allocation in brackets at end of line: "[3 marks]" or "(3)"
_MARKS_PATTERN = re.compile(r"\[(\d+)\s*marks?\]|\((\d+)\)\s*$", re.IGNORECASE)

# Mark scheme: section header "Question N" (case-insensitive, line by itself)
_MS_QUESTION_HEADER = re.compile(
    r"(?m)^Question\s+(\d{1,2}[a-z]?)\s*$", re.IGNORECASE
)

# Mark type indicator at start of line: "M1", "A1", "B2", "dM1", "ft"
_MARK_TYPE_LINE = re.compile(
    r"^\s*(d{0,2}[Mm]|[AaBbEeQq]|[Ff][Tt])\s*(\d+)?\s*[:\s]",
)

# Examiner report section headers
_REPORT_QUESTION_HEADER = re.compile(
    r"(?m)^(?:Question|Q\.?)\s+(\d+[a-z]?)",
    re.IGNORECASE,
)


def extract_question_blocks(raw_text: str) -> list[dict[str, Any]]:
    """Parse raw OCR text into individual question blocks.

    Each block: {question_number, raw_text, marks, sub_parts: [...]}.
    """
    lines = raw_text.splitlines()
    blocks: list[dict[str, Any]] = []
    current_block: dict[str, Any] | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        if current_block is not None and current_lines:
            text = "\n".join(current_lines).strip()
            marks = _extract_marks(text)
            current_block["raw_text"] = text
            current_block["marks"] = marks
            current_block["sub_parts"] = _extract_sub_parts(text)
            blocks.append(current_block)

    for line in lines:
        m = _QUESTION_START.match(line)
        if m:
            _flush()
            q_num = m.group(1) or m.group(2) or m.group(3)
            current_block = {"question_number": q_num}
            current_lines = [line]
        elif current_block is not None:
            current_lines.append(line)

    _flush()

    if not blocks:
        logger.warning("No question blocks found in text (len=%d)", len(raw_text))

    return blocks


def _extract_marks(text: str) -> int:
    """Return total marks from the last marks bracket in text, or 0."""
    matches = list(_MARKS_PATTERN.finditer(text))
    if not matches:
        return 0
    last = matches[-1]
    val = last.group(1) or last.group(2)
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _extract_sub_parts(text: str) -> list[dict[str, Any]]:
    """Extract sub-parts (a), (b), (i), (ii) from a question block."""
    sub_pattern = re.compile(r"(?m)^\s*\(([a-z]{1,3}|i{1,4}|iv|vi{0,3})\)\s+")
    parts: list[dict[str, Any]] = []
    positions = [(m.start(), m.group(1)) for m in sub_pattern.finditer(text)]
    for idx, (start, label) in enumerate(positions):
        end = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
        part_text = text[start:end].strip()
        parts.append({
            "label": label,
            "raw_text": part_text,
            "marks": _extract_marks(part_text),
        })
    return parts


def extract_markscheme_blocks(raw_text: str) -> list[dict[str, Any]]:
    """Parse raw OCR text of a mark scheme into mark entries per question.

    Each entry: {question_number, sequence, mark_type, marks_value, description, conditionality}.
    Mark schemes use "Question N" headers (no trailing period), so this function
    uses a dedicated header pattern rather than the question paper block parser.
    """
    entries: list[dict[str, Any]] = []

    # Split on "Question N" section headers
    sections = _MS_QUESTION_HEADER.split(raw_text)
    # split() with a capturing group returns [preamble, q1, body1, q2, body2, ...]
    if len(sections) <= 1:
        # Fallback: try question paper style parsing
        blocks = extract_question_blocks(raw_text)
        for block in blocks:
            entries.extend(_parse_mark_lines(block["question_number"], block["raw_text"]))
        return entries

    it = iter(sections[1:])
    for q_num, body in zip(it, it):
        entries.extend(_parse_mark_lines(q_num.strip(), body))

    return entries


def _parse_mark_lines(q_num: str, body: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seq = 1
    for line in body.splitlines():
        m = _MARK_TYPE_LINE.match(line)
        if m:
            raw_type = m.group(1)
            mark_type = _normalise_mark_type(raw_type)
            marks_val = int(m.group(2)) if m.group(2) else 1
            description = line.strip()
            conditionality = _extract_conditionality(line)
            entries.append({
                "question_number": q_num,
                "sequence": seq,
                "mark_type": mark_type,
                "marks_value": marks_val,
                "description": description,
                "conditionality": conditionality,
            })
            seq += 1
    return entries


def _normalise_mark_type(raw: str) -> str:
    mapping = {
        "dm": "dM", "ddm": "ddM", "ft": "ft",
        "m": "M", "a": "A", "b": "B", "e": "E", "q": "Q",
    }
    return mapping.get(raw.lower(), "M")


def _extract_conditionality(line: str) -> str | None:
    lower = line.lower()
    if "dep" in lower:
        return "dependent"
    if "ft" in lower or "follow" in lower:
        return "follow_through"
    return None


def extract_report_observations(raw_text: str) -> list[dict[str, Any]]:
    """Parse raw OCR text of an examiner report into observation records.

    Each record: {question_number, topic, observation_type, description, emphasis_level}.
    """
    observations: list[dict[str, Any]] = []
    sections = _REPORT_QUESTION_HEADER.split(raw_text)

    it = iter(sections[1:])
    for q_num, body in zip(it, it):
        for obs in _parse_observation_body(q_num.strip(), body):
            observations.append(obs)

    if not observations:
        logger.warning("No observations extracted from examiner report (len=%d)", len(raw_text))

    return observations


_EMPHASIS_HIGH = re.compile(r"\b(many|most|majority|common(ly)?|frequently|often)\b", re.I)
_EMPHASIS_MED  = re.compile(r"\b(some|several|number of|tendency)\b", re.I)
_OBS_TYPE_MAP  = [
    (re.compile(r"\b(misconception|misunderstand|confused)\b", re.I), "misconception"),
    (re.compile(r"\b(error|mistake|incorrect|wrong)\b", re.I), "common_error"),
    (re.compile(r"\b(weak|struggle|difficult|poor)\b", re.I), "weak_area"),
    (re.compile(r"\b(command word|did not|failed to|did not read)\b", re.I), "command_word_failure"),
    (re.compile(r"\b(well|good|correct|excellent|successfully)\b", re.I), "positive_note"),
]


def _parse_observation_body(q_num: str, body: str) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    sentences = re.split(r"(?<=[.!?])\s+", body.strip())
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue

        obs_type = "emphasis"
        for pattern, label in _OBS_TYPE_MAP:
            if pattern.search(sentence):
                obs_type = label
                break

        if _EMPHASIS_HIGH.search(sentence):
            level = 3
        elif _EMPHASIS_MED.search(sentence):
            level = 2
        else:
            level = 1

        observations.append({
            "question_number": q_num,
            "topic": None,
            "observation_type": obs_type,
            "description": sentence,
            "emphasis_level": level,
        })

    return observations

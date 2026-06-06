"""Tests for ingestion/extractor.py question block parsing."""
from __future__ import annotations

import pytest
from ingestion.extractor import (
    extract_question_blocks,
    extract_markscheme_blocks,
    extract_report_observations,
)

SAMPLE_QP = """
1. Find the value of x such that 2x + 5 = 13.
                                                [2 marks]

2. Differentiate f(x) = 3x^2 + 2x - 7 with respect to x.
                                                [3 marks]

3. Prove that the sum of two odd numbers is always even.
                                                [4 marks]
"""

SAMPLE_MS = """
Question 1
M1: Rearrange equation: 2x = 8
A1: x = 4

Question 2
M1: Apply power rule to 3x^2
A1: 6x
A1: f'(x) = 6x + 2
"""

SAMPLE_ER = """
Question 1
Many candidates correctly rearranged the equation. Some students made an error in subtraction.

Question 2
Most students differentiated 3x^2 correctly. However, some candidates showed a misconception about constants.
"""


def test_extract_question_blocks_count():
    blocks = extract_question_blocks(SAMPLE_QP)
    assert len(blocks) == 3


def test_extract_question_blocks_numbers():
    blocks = extract_question_blocks(SAMPLE_QP)
    numbers = [b["question_number"] for b in blocks]
    assert "1" in numbers
    assert "2" in numbers
    assert "3" in numbers


def test_extract_question_blocks_marks():
    blocks = extract_question_blocks(SAMPLE_QP)
    by_num = {b["question_number"]: b for b in blocks}
    assert by_num["1"]["marks"] == 2
    assert by_num["2"]["marks"] == 3
    assert by_num["3"]["marks"] == 4


def test_extract_markscheme_blocks():
    entries = extract_markscheme_blocks(SAMPLE_MS)
    assert len(entries) >= 3
    types = {e["mark_type"] for e in entries}
    assert "M" in types
    assert "A" in types


def test_extract_report_observations():
    obs = extract_report_observations(SAMPLE_ER)
    assert len(obs) >= 2
    types = {o["observation_type"] for o in obs}
    # Should detect at least positive_note or misconception
    assert types & {"positive_note", "misconception", "common_error"}


def test_sub_parts_extraction():
    text = """
1. A curve has equation y = x^3 - 3x + 2.

(a) Find dy/dx.
                [2 marks]

(b) Determine the coordinates of any stationary points.
                [3 marks]
"""
    blocks = extract_question_blocks(text)
    assert len(blocks) >= 1
    q1 = blocks[0]
    assert len(q1["sub_parts"]) == 2
    assert q1["sub_parts"][0]["label"] == "a"
    assert q1["sub_parts"][1]["label"] == "b"


def test_empty_text_returns_empty_list():
    blocks = extract_question_blocks("")
    assert blocks == []

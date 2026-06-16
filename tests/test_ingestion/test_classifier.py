"""Tests for ingestion/classifier.py."""
from __future__ import annotations

from ingestion.classifier import (
    extract_command_word,
    classify_difficulty,
    classify_tags,
    classify_topic,
)


def test_extract_command_word_find():
    assert extract_command_word("Find the value of x.") == "find"


def test_extract_command_word_show_that():
    assert extract_command_word("Show that n^2 + n is always even.") == "show that"


def test_extract_command_word_prove_that():
    # "Prove that" is longer match than "prove" — longest-match wins
    assert extract_command_word("Prove that the series converges.") == "prove that"


def test_extract_command_word_prove_standalone():
    # "Prove" without "that" should return "prove"
    assert extract_command_word("Prove the result.") == "prove"


def test_extract_command_word_none():
    assert extract_command_word("The curve passes through the origin.") is None


def test_classify_difficulty_low_marks_state():
    q = {"marks": 1, "command_word": "state", "raw_text": "State the value."}
    assert classify_difficulty(q) == 1


def test_classify_difficulty_proof_high_marks():
    q = {"marks": 6, "command_word": "prove", "raw_text": "Prove that f(x) > 0 for all real x."}
    assert classify_difficulty(q) == 5


def test_classify_difficulty_find_medium():
    q = {"marks": 3, "command_word": "find", "raw_text": "Find the roots."}
    d = classify_difficulty(q)
    assert 1 <= d <= 4


def test_classify_tags_proof():
    q = {"raw_text": "Show that 2^n > n^2 for n >= 5."}
    tags = classify_tags(q)
    assert "Proof" in tags


def test_classify_tags_diagram():
    q = {"raw_text": "Sketch the curve y = ln(x)."}
    tags = classify_tags(q)
    assert "Diagram Based" in tags


def test_classify_tags_calculation():
    q = {"raw_text": "Find the value of the integral from 0 to pi."}
    tags = classify_tags(q)
    assert "Calculation" in tags


def test_classify_tags_no_duplicates():
    q = {"raw_text": "Evaluate and sketch the curve y = x^2."}
    tags = classify_tags(q)
    assert len(tags) == len(set(tags))


def test_classify_topic_maths_calculus():
    q = {"raw_text": "Differentiate f(x) = 3x^2 + 2x."}
    topic, subtopic = classify_topic(q, "Mathematics", "P2")
    assert topic == "Calculus"
    assert subtopic == "Differentiation"


def test_classify_topic_physics_waves():
    q = {"raw_text": "Calculate the frequency of the wave given its wavelength."}
    topic, subtopic = classify_topic(q, "Physics", "Unit 4")
    assert topic == "Waves"


def test_classify_topic_fallback():
    q = {"raw_text": "An interesting problem with no recognizable keywords."}
    topic, subtopic = classify_topic(q, "Mathematics", "P1")
    assert topic == "P1"
    assert subtopic == "General"

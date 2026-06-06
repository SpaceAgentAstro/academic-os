"""Tests for Phase 6: briefing generator and telegram message splitting."""
from __future__ import annotations

from briefing.generator import DailyBriefing, format_for_telegram
from agents.delivery.telegram_agent import _split_message


def test_format_for_telegram_structure():
    briefing = DailyBriefing(
        date="2026-06-06",
        section1_academic="*Academic Intelligence*\n• Test misconception.",
        section2_curriculum="*Curriculum Progress*\n• Mathematics: P1: 0%",
        section3_revision="*Adaptive Revision*\n• No questions available.",
        section4_status="*System Status*\n• Papers: 0",
    )
    text = format_for_telegram(briefing)
    assert "Academic OS" in text
    assert "2026-06-06" in text
    assert "*Academic Intelligence*" in text
    assert "*Curriculum Progress*" in text
    assert "*Adaptive Revision*" in text
    assert "*System Status*" in text


def test_format_for_telegram_all_sections_present():
    briefing = DailyBriefing(
        date="2026-06-06",
        section1_academic="S1",
        section2_curriculum="S2",
        section3_revision="S3",
        section4_status="S4",
    )
    text = format_for_telegram(briefing)
    for s in ["S1", "S2", "S3", "S4"]:
        assert s in text


def test_split_message_short():
    chunks = _split_message("Hello world", 4096)
    assert chunks == ["Hello world"]


def test_split_message_exact():
    text = "A" * 4096
    chunks = _split_message(text, 4096)
    assert len(chunks) == 1


def test_split_message_long():
    text = "Line\n" * 1000  # 5000 chars
    chunks = _split_message(text, 4096)
    assert len(chunks) >= 2
    # Each chunk must be <= 4096
    for chunk in chunks:
        assert len(chunk) <= 4096
    # Reconstruct must contain all content
    reconstructed = "\n".join(chunks)
    assert len(reconstructed) >= len(text) - len(chunks)  # allow for stripped newlines


def test_split_message_no_newline():
    text = "A" * 5000
    chunks = _split_message(text, 4096)
    assert len(chunks) == 2
    assert len(chunks[0]) == 4096
    assert len(chunks[1]) == 904


def test_briefing_dataclass_defaults():
    briefing = DailyBriefing(date="2026-01-01")
    assert briefing.section1_academic == ""
    assert briefing.section2_curriculum == ""
    assert briefing.section3_revision == ""
    assert briefing.section4_status == ""

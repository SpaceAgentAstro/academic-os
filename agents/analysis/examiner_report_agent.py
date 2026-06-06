from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, date, timezone
from pathlib import Path

from ingestion.ocr import extract_full_text
from ingestion.extractor import extract_report_observations

logger = logging.getLogger(__name__)


@dataclass
class Observation:
    question_number: str | None
    topic: str | None
    subtopic: str | None
    observation_type: str
    description: str
    emphasis_level: int = 1


def extract_observations(pdf_path: Path) -> list[Observation]:
    """Extract all observations from an examiner report PDF."""
    full_text = extract_full_text(pdf_path)
    raw_obs = extract_report_observations(full_text)
    return [
        Observation(
            question_number=o.get("question_number"),
            topic=o.get("topic"),
            subtopic=None,
            observation_type=o["observation_type"],
            description=o["description"],
            emphasis_level=o.get("emphasis_level", 1),
        )
        for o in raw_obs
    ]


def _ensure_report(
    er_conn: sqlite3.Connection,
    paper_id: int,
    year: int,
    session: str,
    subject: str,
    module_code: str,
    raw_text: str,
) -> int:
    """Insert or retrieve a report record. Returns report_id."""
    now = datetime.now(timezone.utc).isoformat()
    er_conn.execute(
        """
        INSERT INTO reports (paper_id, year, session, subject, module_code, raw_text, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(paper_id) DO UPDATE SET processed_at=excluded.processed_at
        """,
        (paper_id, year, session, subject, module_code, raw_text, now),
    )
    row = er_conn.execute("SELECT id FROM reports WHERE paper_id=?", (paper_id,)).fetchone()
    return row[0]


def _write_observation(
    er_conn: sqlite3.Connection,
    report_id: int,
    obs: Observation,
    question_id: int | None,
) -> int:
    """Insert a single observation. Returns observation_id."""
    cur = er_conn.execute(
        """
        INSERT INTO observations
            (report_id, question_id, topic, subtopic, observation_type, description, emphasis_level)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report_id, question_id, obs.topic, obs.subtopic,
            obs.observation_type, obs.description, obs.emphasis_level,
        ),
    )
    return cur.lastrowid  # type: ignore[return-value]


def _upsert_misconception(
    er_conn: sqlite3.Connection,
    obs: Observation,
    obs_id: int,
    subject: str,
    module_code: str,
) -> None:
    """Persist a misconception and link it to its source observation."""
    if obs.observation_type != "misconception":
        return
    today = date.today().isoformat()
    topic = obs.topic or "General"
    er_conn.execute(
        """
        INSERT INTO misconceptions
            (subject, module_code, topic, subtopic, description, frequency, last_seen, is_active)
        VALUES (?, ?, ?, ?, ?, 1, ?, 1)
        ON CONFLICT(subject, module_code, topic, description) DO UPDATE SET
            frequency = frequency + 1,
            last_seen = excluded.last_seen,
            is_active = 1
        """,
        (subject, module_code, topic, obs.subtopic, obs.description, today),
    )
    # Re-query the ID after UPSERT (lastrowid is 0 on UPDATE path)
    row = er_conn.execute(
        "SELECT id FROM misconceptions WHERE subject=? AND module_code=? AND topic=? AND description=?",
        (subject, module_code, topic, obs.description),
    ).fetchone()
    if row:
        er_conn.execute(
            """
            INSERT OR IGNORE INTO misconception_sources (misconception_id, observation_id)
            VALUES (?, ?)
            """,
            (row[0], obs_id),
        )


def ingest_report(
    pdf_path: Path,
    paper_id: int,
    year: int,
    session: str,
    subject: str,
    module_code: str,
    er_conn: sqlite3.Connection | None = None,
    qb_conn: sqlite3.Connection | None = None,
) -> None:
    """Full report ingestion: extract observations → write to examiner_reports.db."""
    from config.settings import DB_EXAMINER, DB_QUESTION_BANK
    from db.models import get_db

    logger.info("Ingesting examiner report: %s", pdf_path.name)
    raw_text = extract_full_text(pdf_path)
    observations = extract_observations(pdf_path)

    def _run(er: sqlite3.Connection, qb: sqlite3.Connection) -> None:
        report_id = _ensure_report(er, paper_id, year, session, subject, module_code, raw_text)

        for obs in observations:
            question_id: int | None = None
            if obs.question_number:
                row = qb.execute(
                    "SELECT id FROM questions WHERE paper_id=? AND question_number=?",
                    (paper_id, obs.question_number),
                ).fetchone()
                if row:
                    question_id = row[0]

            obs_id = _write_observation(er, report_id, obs, question_id)
            _upsert_misconception(er, obs, obs_id, subject, module_code)

        er.commit()
        logger.info(
            "Report ingested: %d observations for paper_id=%d", len(observations), paper_id
        )

    if er_conn is not None and qb_conn is not None:
        _run(er_conn, qb_conn)
    else:
        with get_db(DB_EXAMINER) as er, get_db(DB_QUESTION_BANK) as qb:
            _run(er, qb)

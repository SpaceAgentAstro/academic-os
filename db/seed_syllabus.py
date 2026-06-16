"""Seed progress.db with syllabus data from db/syllabus/*.json.

Usage:
    PYTHONPATH=. python db/seed_syllabus.py [--dry-run]

Idempotent: uses INSERT OR IGNORE so re-runs are safe.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_SYLLABUS_DIR = Path(__file__).parent / "syllabus"
_SYLLABUS_FILES = [
    "mathematics.json",
    "further_mathematics.json",
    "physics.json",
    "chemistry.json",
    "computer_science.json",
]


def seed_all(conn=None, dry_run: bool = False) -> dict[str, int]:
    """Seed all subjects from JSON files into progress.db.

    Returns a dict {filename: spec_points_inserted}.
    """
    from config.settings import DB_PROGRESS
    from db.models import get_db

    def _run(c) -> dict[str, int]:
        totals: dict[str, int] = {}
        for fname in _SYLLABUS_FILES:
            path = _SYLLABUS_DIR / fname
            if not path.exists():
                logger.warning("Syllabus file missing: %s", path)
                continue
            with open(path) as f:
                data = json.load(f)
            count = _seed_subject(c, data, dry_run=dry_run)
            totals[fname] = count
            logger.info("%s: %d spec points seeded", fname, count)
        if not dry_run:
            # Materialise spaced-repetition state from the seeded topic tree as a
            # side effect. Deliberately not added to `totals` (which is the per-file
            # spec-point count contract) so the return value stays idempotent.
            sr_count = _seed_spaced_repetition(c)
            logger.info("spaced_repetition_items: %d topics materialised", sr_count)
            c.commit()
        return totals

    if conn is not None:
        return _run(conn)
    with get_db(DB_PROGRESS) as c:
        return _run(c)


def _seed_subject(conn, data: dict, dry_run: bool = False) -> int:
    """Insert one subject tree. Returns number of spec_points inserted."""
    subj = data["subject"]
    if not dry_run:
        conn.execute(
            """
            INSERT OR IGNORE INTO subjects (name, board, qualification, code)
            VALUES (?, ?, ?, ?)
            """,
            (subj["name"], subj["board"], subj["qualification"], subj["code"]),
        )
    subject_id = conn.execute(
        "SELECT id FROM subjects WHERE code = ?", (subj["code"],)
    ).fetchone()
    if subject_id is None:
        if dry_run:
            # Simulate ID for dry run
            subject_id = (-1,)
        else:
            raise RuntimeError(f"Subject {subj['code']} not found after insert")
    subject_id = subject_id[0]

    total_spec_points = 0
    for mod in data.get("modules", []):
        if not dry_run:
            conn.execute(
                """
                INSERT OR IGNORE INTO modules (subject_id, name, code, sequence)
                VALUES (?, ?, ?, ?)
                """,
                (subject_id, mod["name"], mod["code"], mod.get("sequence", 0)),
            )
        module_id_row = conn.execute(
            "SELECT id FROM modules WHERE subject_id = ? AND code = ?",
            (subject_id, mod["code"]),
        ).fetchone()
        module_id = module_id_row[0] if module_id_row else -1

        for topic in mod.get("topics", []):
            if not dry_run:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO topics (module_id, name, sequence)
                    VALUES (?, ?, ?)
                    """,
                    (module_id, topic["name"], topic.get("sequence", 0)),
                )
            topic_id_row = conn.execute(
                "SELECT id FROM topics WHERE module_id = ? AND name = ?",
                (module_id, topic["name"]),
            ).fetchone()
            topic_id = topic_id_row[0] if topic_id_row else -1

            for subtopic in topic.get("subtopics", []):
                if not dry_run:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO subtopics (topic_id, name, sequence)
                        VALUES (?, ?, ?)
                        """,
                        (topic_id, subtopic["name"], subtopic.get("sequence", 0)),
                    )
                subtopic_id_row = conn.execute(
                    "SELECT id FROM subtopics WHERE topic_id = ? AND name = ?",
                    (topic_id, subtopic["name"]),
                ).fetchone()
                subtopic_id = subtopic_id_row[0] if subtopic_id_row else -1

                for sp in subtopic.get("spec_points", []):
                    if not dry_run:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO specification_points
                                (subtopic_id, spec_ref, description)
                            VALUES (?, ?, ?)
                            """,
                            (subtopic_id, sp["spec_ref"], sp["description"]),
                        )
                    total_spec_points += 1

    return total_spec_points


def _seed_spaced_repetition(conn) -> int:
    """Materialise one spaced-repetition item per syllabus topic.

    Reads the normalised topic tree that the subject seeders just populated and
    creates an initial SM-2 state row per (subject, module, topic). Idempotent:
    ``INSERT OR IGNORE`` against the ``UNIQUE(subject, unit, topic)`` constraint
    means re-runs never duplicate rows or reset progress on existing topics.
    """
    rows = conn.execute(
        """
        SELECT s.name AS subject, m.code AS unit, t.name AS topic
        FROM topics t
        JOIN modules m ON m.id = t.module_id
        JOIN subjects s ON s.id = m.subject_id
        ORDER BY s.name, m.sequence, t.sequence
        """
    ).fetchall()

    inserted = 0
    for subject, unit, topic in rows:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO spaced_repetition_items
                (subject, unit, topic, mastery, ease_factor, interval_days, due_date)
            VALUES (?, ?, ?, 0.0, 2.5, 1.0, DATE('now'))
            """,
            (subject, unit or "", topic),
        )
        inserted += cur.rowcount
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("Dry run — no changes will be written")
    totals = seed_all(dry_run=dry_run)
    for fname, count in totals.items():
        print(f"  {fname}: {count} spec points")
    print(f"Total: {sum(totals.values())} spec points")

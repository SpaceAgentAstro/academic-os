from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DIAGRAM_TYPES_BY_SUBJECT: dict[str, list[str]] = {
    "Physics": ["circuit", "electric_field", "magnetic_field", "mechanics",
                "vector", "physics_graph", "wave", "ray_diagram"],
    "Chemistry": ["reaction_mechanism", "spectrum", "molecular_structure",
                  "lab_apparatus", "energy_profile"],
    "Mathematics": ["function_graph", "geometric_figure", "statistical_chart",
                    "coordinate_geometry"],
    "Computer Science": ["logic_gate", "flowchart", "network_diagram",
                         "system_architecture", "state_machine", "entity_relationship"],
}

# Keyword → diagram_type heuristic (used when pix2tex/CLIP not available)
_FILENAME_HINTS: list[tuple[str, str]] = [
    ("circuit", "circuit"),
    ("wave", "wave"),
    ("graph", "function_graph"),
    ("stat", "statistical_chart"),
    ("flow", "flowchart"),
    ("logic", "logic_gate"),
    ("network", "network_diagram"),
    ("molecule", "molecular_structure"),
    ("spectrum", "spectrum"),
    ("force", "mechanics"),
    ("vector", "vector"),
    ("ray", "ray_diagram"),
    ("energy", "energy_profile"),
    ("coord", "coordinate_geometry"),
]

_VALID_TYPES = {
    "circuit", "electric_field", "magnetic_field", "mechanics", "vector",
    "physics_graph", "wave", "ray_diagram", "reaction_mechanism", "spectrum",
    "molecular_structure", "lab_apparatus", "energy_profile", "function_graph",
    "geometric_figure", "statistical_chart", "coordinate_geometry", "logic_gate",
    "flowchart", "network_diagram", "system_architecture", "state_machine",
    "entity_relationship", "table", "other",
}


def classify_diagram(image_path: Path, subject: str) -> str:
    """Classify a diagram image into one of the subject-specific diagram types.

    Uses filename hint heuristics. Falls back to 'other'.
    """
    name_lower = image_path.stem.lower()
    for hint, dtype in _FILENAME_HINTS:
        if hint in name_lower:
            if dtype in _VALID_TYPES:
                return dtype
    return "other"


def _get_image_dimensions(image_path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            return img.width, img.height
    except Exception:
        return None, None


def _write_diagram(
    diag_conn: sqlite3.Connection,
    image_path: Path,
    source_file: str,
    page_number: int,
    subject: str,
    module_code: str,
    diagram_type: str,
    description: str | None,
) -> int:
    """Insert a diagram record. Returns diagram_id."""
    width, height = _get_image_dimensions(image_path)
    now = datetime.now(timezone.utc).isoformat()
    cur = diag_conn.execute(
        """
        INSERT INTO diagrams
            (source_file, page_number, image_path, subject, module_code,
             diagram_type, description, width_px, height_px, processed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(image_path) DO UPDATE SET
            diagram_type=excluded.diagram_type,
            description=excluded.description,
            processed_at=excluded.processed_at
        """,
        (
            source_file, page_number, str(image_path), subject, module_code,
            diagram_type, description, width, height, now,
        ),
    )
    return cur.lastrowid  # type: ignore[return-value]


def _link_diagram_to_question(
    diag_conn: sqlite3.Connection,
    diagram_id: int,
    question_id: int,
    position: str | None = None,
) -> None:
    diag_conn.execute(
        """
        INSERT OR IGNORE INTO diagram_question_links (diagram_id, question_id, position)
        VALUES (?, ?, ?)
        """,
        (diagram_id, question_id, position),
    )


def process_images_from_paper(
    image_paths: list[Path],
    subject: str,
    module_code: str,
    source_file: str,
    question_id: int | None = None,
    diag_conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    """Classify and store all images extracted from a paper.

    Returns list of {image_path, diagram_type, diagram_id}.
    Accepts optional diag_conn for testability.
    """
    from config.settings import DB_DIAGRAMS
    from db.models import get_db

    results: list[dict[str, Any]] = []

    def _run(conn: sqlite3.Connection) -> None:
        for img_path in image_paths:
            dtype = classify_diagram(img_path, subject)
            page_num = _infer_page_number(img_path)
            diagram_id = _write_diagram(
                conn, img_path, source_file, page_num,
                subject, module_code, dtype, None,
            )
            if question_id is not None:
                _link_diagram_to_question(conn, diagram_id, question_id)
            results.append({
                "image_path": str(img_path),
                "diagram_type": dtype,
                "diagram_id": diagram_id,
            })
        conn.commit()
        logger.info("Processed %d images from %s", len(image_paths), source_file)

    if diag_conn is not None:
        _run(diag_conn)
    else:
        with get_db(DB_DIAGRAMS) as conn:
            _run(conn)

    return results


def _infer_page_number(image_path: Path) -> int:
    """Extract page number from filename pattern <stem>_page_<n>.png."""
    import re
    m = re.search(r"_page_(\d+)", image_path.stem)
    return int(m.group(1)) if m else 0

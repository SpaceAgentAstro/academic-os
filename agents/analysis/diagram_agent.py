from __future__ import annotations

import logging
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


def classify_diagram(image_path: Path, subject: str) -> str:
    """Classify a diagram image into one of the subject-specific diagram types."""
    raise NotImplementedError


def process_images_from_paper(
    image_paths: list[Path],
    subject: str,
    module_code: str,
    source_file: str,
    question_id: int | None = None,
) -> list[dict[str, Any]]:
    """Classify and store all images extracted from a paper."""
    raise NotImplementedError

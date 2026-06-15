"""Regression tests locking in the Errors/ remediation cycle.

Each test maps to one or more fixed issues (LOGIC-/RT-/AOS-/SYN-) so a
re-introduction of the bug fails CI. The suite spins up a temporary DATA_DIR,
initialises + seeds the databases, and drives the FastAPI app via TestClient.
"""
from __future__ import annotations

import importlib
import os
import tempfile

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")


@pytest.fixture(scope="module")
def client_and_ids():
    tmp = tempfile.mkdtemp(prefix="aos_api_test_")
    os.environ["DATA_DIR"] = tmp

    # Re-import settings/models/app against the temp DATA_DIR.
    import config.settings as settings
    importlib.reload(settings)
    import db.models as models
    importlib.reload(models)

    from db.seed_syllabus import seed_all
    models.init_all_databases()
    seed_all()

    with models.get_db(settings.DB_QUESTION_BANK) as c:
        c.execute(
            "INSERT INTO papers (qualification,subject,module_code,paper_code,session,year,"
            "paper_type,source_file,processed_at) VALUES "
            "('IAL','Mathematics','P1','WMA11/01','January 2024',2024,'question_paper','f.pdf','2024-01-01')"
        )
        pid = c.execute("SELECT id FROM papers LIMIT 1").fetchone()[0]
        c.execute(
            "INSERT INTO questions (paper_id,question_number,marks,difficulty,raw_text,has_diagram) "
            "VALUES (?, '1', 5, 3, 'Differentiate y = x^2 wrt x and show full working here please.', 0)",
            (pid,),
        )
        qid = c.execute("SELECT id FROM questions LIMIT 1").fetchone()[0]
        c.execute(
            "INSERT INTO question_topics (question_id,subject,module_code,topic,subtopic,is_primary) "
            "VALUES (?, 'Mathematics','P1','Differentiation','Chain Rule',1)",
            (qid,),
        )
        # A second paper/question for the cross-paper attempt check.
        c.execute(
            "INSERT INTO papers (qualification,subject,module_code,paper_code,session,year,"
            "paper_type,source_file,processed_at) VALUES "
            "('IAL','Mathematics','P2','WMA12/01','January 2024',2024,'question_paper','g.pdf','2024-01-01')"
        )
        pid2 = c.execute("SELECT id FROM papers WHERE module_code='P2'").fetchone()[0]
        c.execute(
            "INSERT INTO questions (paper_id,question_number,marks,difficulty,raw_text,has_diagram) "
            "VALUES (?, '1', 4, 2, 'Integrate 2x with respect to x over a suitable interval here.', 0)",
            (pid2,),
        )
        qid2 = c.execute("SELECT id FROM questions WHERE paper_id=?", (pid2,)).fetchone()[0]

    import backend.main as backend_main
    importlib.reload(backend_main)
    client = fastapi_testclient.TestClient(backend_main.app, raise_server_exceptions=False)
    return client, backend_main, {"pid": pid, "qid": qid, "pid2": pid2, "qid2": qid2}


# --- LOGIC-001 / RT-001: spaced_repetition_items exists and is seeded --------
def test_sr_table_seeded(client_and_ids):
    client, backend_main, _ = client_and_ids
    import config.settings as settings
    from db.models import get_db
    with get_db(settings.DB_PROGRESS) as c:
        n = c.execute("SELECT COUNT(*) FROM spaced_repetition_items").fetchone()[0]
    assert n > 0


def test_dashboard_and_health_ok(client_and_ids):
    client, _, _ = client_and_ids
    for ep in ("/api/health", "/api/dashboard", "/api/briefing", "/api/status",
               "/api/coverage", "/api/analytics", "/api/weaknesses"):
        assert client.get(ep).status_code == 200, ep


# --- LOGIC-008: dashboard exposes paper_stats over all sessions --------------
def test_paper_stats_present(client_and_ids):
    client, _, _ = client_and_ids
    d = client.get("/api/dashboard").json()
    assert "paper_stats" in d
    assert set(d["paper_stats"]) == {"completed_count", "average_pct"}


# --- AOS-007: limit is clamped ----------------------------------------------
def test_limit_clamped(client_and_ids):
    client, _, _ = client_and_ids
    assert client.get("/api/papers?limit=99999999").status_code == 422
    assert client.get("/api/papers?limit=10").status_code == 200


# --- RT-002 + LOGIC-004: mastery advances and re-marks replace ---------------
def test_attempt_updates_mastery_and_dedups(client_and_ids):
    client, _, ids = client_and_ids
    import config.settings as settings
    from db.models import get_db
    sid = client.post("/api/sessions", json={"paper_id": ids["pid"]}).json()["session_id"]
    r1 = client.post("/api/attempts", json={
        "session_id": sid, "question_id": ids["qid"],
        "marks_awarded": 4, "marks_available": 5, "confidence": 4, "mistake_types": ["Algebra"],
    })
    assert r1.status_code == 200
    assert r1.json()["new_mastery"] is not None  # RT-002: not a silent no-op
    assert "grade_contribution" not in r1.json()  # LOGIC-019 removed
    client.post("/api/attempts", json={
        "session_id": sid, "question_id": ids["qid"],
        "marks_awarded": 5, "marks_available": 5, "confidence": 5, "mistake_types": [],
    })
    with get_db(settings.DB_ATTEMPTS) as c:
        cnt = c.execute(
            "SELECT COUNT(*) FROM attempts WHERE session_id=? AND question_id=?",
            (sid, ids["qid"]),
        ).fetchone()[0]
    assert cnt == 1  # LOGIC-004: re-mark replaced, not duplicated


# --- AOS-011: client path traversal is rejected -----------------------------
def test_path_traversal_rejected(client_and_ids):
    client, _, ids = client_and_ids
    r = client.post("/api/attempts", json={
        "question_id": ids["qid"], "marks_awarded": 1, "marks_available": 2,
        "confidence": 3, "answer_image_path": "../../etc/passwd",
    })
    assert r.status_code == 422


# --- LOGIC-020 / AOS-012: question must belong to the session's paper --------
def test_cross_paper_attempt_rejected(client_and_ids):
    client, _, ids = client_and_ids
    sid = client.post("/api/sessions", json={"paper_id": ids["pid"]}).json()["session_id"]
    r = client.post("/api/attempts", json={
        "session_id": sid, "question_id": ids["qid2"],  # belongs to a different paper
        "marks_awarded": 1, "marks_available": 2, "confidence": 3,
    })
    assert r.status_code == 422


# --- RT-004: spaced-repetition interval is clamped (no date overflow) --------
def test_interval_clamp_survives_many_strong_attempts(client_and_ids):
    client, _, ids = client_and_ids
    for _ in range(40):
        r = client.post("/api/attempts", json={
            "question_id": ids["qid"], "marks_awarded": 5, "marks_available": 5, "confidence": 5,
        })
        assert r.status_code == 200


# --- LOGIC-009: out-of-range difficulty degrades, never 500 ------------------
def test_difficulty_label_guard():
    import backend.main as backend_main
    assert backend_main._difficulty_label(3) == "Multi-step"
    assert backend_main._difficulty_label(0) == ""
    assert backend_main._difficulty_label(99) == ""
    assert backend_main._difficulty_label(None) == ""


# --- LOGIC-003: exam-percentage grades use Edexcel boundaries ----------------
def test_grade_from_pct_boundaries():
    import backend.main as backend_main
    assert backend_main._grade_from_pct(72) == "B"   # was "A" under mastery bands
    assert backend_main._grade_from_pct(90) == "A*"
    assert backend_main._grade_from_pct(39) == "U"


# --- AOS-001: API key gate (default-deny when configured) --------------------
def test_api_key_gate(client_and_ids, monkeypatch):
    client, backend_main, _ = client_and_ids
    monkeypatch.setattr(backend_main, "API_KEY", "secret123")
    assert client.get("/api/health").status_code == 200          # public probe
    assert client.get("/api/dashboard").status_code == 401        # missing key
    assert client.get("/api/dashboard", headers={"X-API-Key": "secret123"}).status_code == 200
    assert client.get("/api/dashboard", headers={"Authorization": "Bearer secret123"}).status_code == 200

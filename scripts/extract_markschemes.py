"""Batch markscheme extraction with robust paper matching.

Matches each mark scheme PDF to its question paper by exam code + nearest
preceding exam date (handles mark-scheme publication lag), or by session
string for the 'Markscheme-UnitN(CODE)-Session' naming style.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.models import get_db
from config.settings import DB_QUESTION_BANK, DB_MARKSCHEME
from agents.analysis.markscheme_agent import ingest_markscheme

PAPERS_DIR = ROOT / "papers"

EXAM_CODE = re.compile(r"([A-Z]{3}\d{2})", re.I)
DATE8 = re.compile(r"(20\d{6})")
SESSION = re.compile(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*?(20\d{2})", re.I)

# Only WPH14 when --wph14 passed, else everything
ONLY_WPH14 = "--wph14" in sys.argv


def exam_code(s: str) -> str | None:
    m = EXAM_CODE.search(s)
    return m.group(1).upper() if m else None


def is_markscheme(name: str) -> bool:
    low = name.lower()
    return ("msc" in low or "rms" in low or low.startswith("markscheme")) and low.endswith(".pdf")


def load_question_papers():
    """Return list of dicts: {id, code, date, session, basename}."""
    rows = []
    with get_db(DB_QUESTION_BANK) as conn:
        for r in conn.execute(
            "SELECT id, paper_code, source_file, session, year FROM papers WHERE paper_type='question_paper'"
        ):
            src = r["source_file"] or ""
            base = Path(src).name
            code = exam_code(base) or exam_code(r["paper_code"] or "")
            dm = DATE8.search(base)
            date = int(dm.group(1)) if dm else None
            rows.append({
                "id": r["id"],
                "code": code,
                "date": date,
                "session": (r["session"] or "").lower().replace(" ", ""),
                "base": base.lower(),
            })
    return rows


def match_paper(ms_name: str, papers) -> int | None:
    code = exam_code(ms_name)
    if not code:
        return None
    candidates = [p for p in papers if p["code"] == code]
    if not candidates:
        return None

    # Style B: session string present (maths "Markscheme-Unit4(WPH14)-June2023")
    sm = SESSION.search(ms_name)
    if sm and "msc_" not in ms_name.lower() and "rms" not in ms_name.lower() and "_que" not in ms_name.lower():
        sess = (sm.group(1) + sm.group(2)).lower()
        for p in candidates:
            if sess in p["session"] or sess in p["base"]:
                return p["id"]

    # Style A: YYYYMMDD date — nearest preceding within 330 days, else nearest overall
    dm = DATE8.search(ms_name)
    if dm:
        ms_date = int(dm.group(1))
        dated = [p for p in candidates if p["date"]]
        if dated:
            # exact date match first
            for p in dated:
                if p["date"] == ms_date:
                    return p["id"]
            # nearest preceding (publication lag): ms_date - paper_date in [0, ~11 months]
            def days_between(a, b):
                # crude: treat YYYYMMDD ints, convert to ordinal-ish
                from datetime import date
                try:
                    da = date(a // 10000, (a // 100) % 100, a % 100)
                    db_ = date(b // 10000, (b // 100) % 100, b % 100)
                    return (da - db_).days
                except ValueError:
                    return 99999
            preceding = [(p, days_between(ms_date, p["date"])) for p in dated]
            preceding = [(p, d) for p, d in preceding if 0 <= d <= 330]
            if preceding:
                preceding.sort(key=lambda x: x[1])
                return preceding[0][0]["id"]
            # fallback nearest overall within 330 days absolute
            allnear = [(p, abs(days_between(ms_date, p["date"]))) for p in dated]
            allnear = [(p, d) for p, d in allnear if d <= 330]
            if allnear:
                allnear.sort(key=lambda x: x[1])
                return allnear[0][0]["id"]

    # Last resort: if exactly one candidate, use it
    if len(candidates) == 1:
        return candidates[0]["id"]
    return None


def main():
    papers = load_question_papers()
    ms_files = sorted(p for p in PAPERS_DIR.rglob("*.pdf") if is_markscheme(p.name))
    if ONLY_WPH14:
        ms_files = [p for p in ms_files if "wph14" in p.name.lower()]

    print(f"Found {len(ms_files)} mark scheme PDFs, {len(papers)} question papers")
    matched = 0
    unmatched = []
    errors = []
    for i, ms in enumerate(ms_files):
        pid = match_paper(ms.name, papers)
        if pid is None:
            unmatched.append(ms.name)
            continue
        try:
            ingest_markscheme(ms, pid)
            matched += 1
            print(f"[{i+1}/{len(ms_files)}] OK  {ms.name} -> paper {pid}")
        except Exception as exc:
            errors.append((ms.name, str(exc)))
            print(f"[{i+1}/{len(ms_files)}] ERR {ms.name}: {exc}")

    print(f"\n=== matched={matched} unmatched={len(unmatched)} errors={len(errors)} ===")
    if unmatched:
        print("UNMATCHED:", unmatched[:30])
    with get_db(DB_MARKSCHEME) as conn:
        total = conn.execute("SELECT COUNT(*) FROM markscheme_entries").fetchone()[0]
        qs = conn.execute("SELECT COUNT(DISTINCT question_id) FROM markscheme_entries").fetchone()[0]
    print(f"markscheme_entries rows={total} across {qs} questions")


if __name__ == "__main__":
    main()

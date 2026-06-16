"""Batch examiner-report extraction with the same paper-matching logic."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.models import get_db  # noqa: E402  (after sys.path bootstrap)
from config.settings import DB_QUESTION_BANK, DB_EXAMINER  # noqa: E402
from agents.analysis.examiner_report_agent import ingest_report  # noqa: E402

PAPERS_DIR = ROOT / "papers"

EXAM_CODE = re.compile(r"([A-Z]{3}\d{2})", re.I)
DATE8 = re.compile(r"(20\d{6})")
SESSION = re.compile(r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*?(20\d{2})", re.I)


def exam_code(s):
    m = EXAM_CODE.search(s)
    return m.group(1).upper() if m else None


def is_examiner(name):
    low = name.lower()
    return ("pef" in low or "examinerreport" in low or "examiner" in low) and low.endswith(".pdf")


def load_papers():
    rows = []
    with get_db(DB_QUESTION_BANK) as conn:
        for r in conn.execute(
            "SELECT id, paper_code, source_file, session, year, subject, module_code "
            "FROM papers WHERE paper_type='question_paper'"
        ):
            src = r["source_file"] or ""
            base = Path(src).name
            code = exam_code(base) or exam_code(r["paper_code"] or "")
            dm = DATE8.search(base)
            rows.append({
                "id": r["id"], "code": code,
                "date": int(dm.group(1)) if dm else None,
                "session": (r["session"] or "").lower().replace(" ", ""),
                "base": base.lower(),
                "year": r["year"], "subj": r["subject"], "mod": r["module_code"],
                "sess_raw": r["session"],
            })
    return rows


def days_between(a, b):
    from datetime import date
    try:
        da = date(a // 10000, (a // 100) % 100, a % 100)
        db_ = date(b // 10000, (b // 100) % 100, b % 100)
        return (da - db_).days
    except ValueError:
        return 99999


def match(name, papers):
    code = exam_code(name)
    if not code:
        return None
    cands = [p for p in papers if p["code"] == code]
    if not cands:
        return None
    sm = SESSION.search(name)
    if sm and "_que" not in name.lower() and "pef_" not in name.lower() and "-pef-" not in name.lower():
        sess = (sm.group(1) + sm.group(2)).lower()
        for p in cands:
            if sess in p["session"] or sess in p["base"]:
                return p
    dm = DATE8.search(name)
    if dm:
        d = int(dm.group(1))
        dated = [p for p in cands if p["date"]]
        for p in dated:
            if p["date"] == d:
                return p
        prec = [(p, days_between(d, p["date"])) for p in dated]
        prec = [(p, x) for p, x in prec if 0 <= x <= 330]
        if prec:
            prec.sort(key=lambda t: t[1])
            return prec[0][0]
        alln = [(p, abs(days_between(d, p["date"]))) for p in dated]
        alln = [(p, x) for p, x in alln if x <= 330]
        if alln:
            alln.sort(key=lambda t: t[1])
            return alln[0][0]
    if len(cands) == 1:
        return cands[0]
    return None


def main():
    papers = load_papers()
    files = sorted(p for p in PAPERS_DIR.rglob("*.pdf") if is_examiner(p.name))
    print(f"Found {len(files)} examiner PDFs, {len(papers)} question papers")
    matched = unmatched = errors = 0
    for i, f in enumerate(files):
        p = match(f.name, papers)
        if not p:
            unmatched += 1
            continue
        try:
            ingest_report(f, p["id"], p["year"] or 0, p["sess_raw"] or "",
                          p["subj"] or "", p["mod"] or "")
            matched += 1
            if (i + 1) % 25 == 0:
                print(f"[{i+1}/{len(files)}] ... matched={matched}")
        except Exception as exc:
            errors += 1
            print(f"ERR {f.name}: {exc}")
    print(f"\n=== matched={matched} unmatched={unmatched} errors={errors} ===")
    with get_db(DB_EXAMINER) as conn:
        obs = conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
        misc = conn.execute("SELECT COUNT(*) FROM misconceptions").fetchone()[0]
        rep = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    print(f"reports={rep} observations={obs} misconceptions={misc}")


if __name__ == "__main__":
    main()

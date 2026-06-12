"use client";

import { useState } from "react";
import { Badge, Button, Card, GradeBadge, Icon, SectionTitle } from "@/components/ui";
import { gradeFromPct, markingPaper } from "@/lib/data";
import type { Route } from "@/lib/types";

const MISTAKES = [
  "Algebra", "Logarithms", "Units", "Wrong method", "Missed step",
  "Rearrangement", "Definition", "Significant figures", "Sign error", "Other",
];
const CONF_COLORS = [
  "var(--danger)", "var(--warn)", "#C9A227", "var(--accent)", "#0E8A5F",
];

export function Marking({ go }: { go: (r: Route) => void }) {
  const paper = markingPaper;
  const qs = paper.questions;
  const firstUnmarked = qs.findIndex((q) => q.awarded == null);
  const [awarded, setAwarded] = useState<(number | null)[]>(
    qs.map((q) => q.awarded)
  );
  const [active, setActive] = useState(firstUnmarked === -1 ? 0 : firstUnmarked);
  const [tags, setTags] = useState<string[]>([]);
  const [conf, setConf] = useState(3);
  const [uploaded, setUploaded] = useState(false);
  const [ocr, setOcr] = useState(false);
  const [note, setNote] = useState("");

  const q = qs[active];
  const scored = awarded.reduce<number>((a, v) => a + (v ?? 0), 0);
  const possibleSoFar = awarded.reduce<number>(
    (a, v, i) => a + (v == null ? 0 : qs[i].marks), 0
  );
  const markedN = awarded.filter((v) => v != null).length;
  const pct = possibleSoFar > 0 ? Math.round((scored / possibleSoFar) * 100) : 0;
  const liveGrade = gradeFromPct(pct);

  const PILL_BG: Record<string, string> = {
    blue: "var(--primary)",
    green: "var(--accent)",
    amber: "var(--warn)",
    red: "var(--danger)",
    grey: "var(--surface-2)",
  };

  const pillTone = (i: number) => {
    const a = awarded[i];
    if (i === active) return "blue";
    if (a == null) return "grey";
    if (a === 0) return "red";
    if (a === qs[i].marks) return "green";
    return "amber";
  };

  const goTo = (i: number) => {
    setActive(i);
    setTags([]);
    setConf(3);
    setUploaded(false);
    setOcr(false);
    setNote("");
  };

  // Next unmarked question after `from`, wrapping to the start.
  const nextUnmarked = (from: number, marked: (number | null)[]) => {
    for (let step = 1; step <= qs.length; step++) {
      const n = (from + step) % qs.length;
      if (marked[n] == null) return n;
    }
    return -1;
  };

  const save = () => {
    const next = [...awarded];
    if (next[active] == null) next[active] = 0;
    setAwarded(next);
    const n = nextUnmarked(active, next);
    if (n !== -1) goTo(n);
  };

  // Skip leaves the question unmarked rather than recording a zero.
  const skip = () => {
    const n = nextUnmarked(active, awarded);
    if (n !== -1) goTo(n);
  };

  const upload = () => {
    setUploaded(true);
    setOcr(true);
    setTimeout(() => setOcr(false), 1400);
  };

  const toggleTag = (t: string) =>
    setTags((s) => (s.includes(t) ? s.filter((x) => x !== t) : [...s, t]));

  return (
    <div className="aos-page">
      <div className="aos-marking-head">
        <div>
          <h1>
            {paper.code} · {paper.session}
          </h1>
          <p className="aos-page-sub">
            Marking · {markedN} of {qs.length} questions marked
          </p>
        </div>
        <div className="aos-marking-score">
          <div className="aos-live-score">
            {scored}
            <span className="aos-live-max"> / {paper.max}</span>
          </div>
          <div className="aos-live-grade">
            <span>Live grade</span>
            <GradeBadge grade={liveGrade} />
            <span className="aos-muted">{pct}%</span>
          </div>
        </div>
      </div>

      <div className="aos-pill-row">
        {qs.map((qq, i) => {
          const tone = pillTone(i);
          return (
            <button
              key={qq.n}
              className="aos-qpill"
              style={{
                background: PILL_BG[tone],
                color: tone === "grey" ? "var(--text-2)" : "#fff",
                borderColor: tone === "grey" ? "var(--border)" : "transparent",
              }}
              onClick={() => goTo(i)}
            >
              {qq.n}
            </button>
          );
        })}
      </div>

      <div className="aos-mark-split">
        {/* LEFT — question + markscheme */}
        <Card>
          <div className="aos-mark-qhead">
            <span className="aos-mark-qnum">{q.part}</span>
            <Badge tone="primary">{q.marks} marks</Badge>
            <Badge>{q.topic}</Badge>
            <Badge>{q.sub}</Badge>
          </div>
          <p className="aos-mark-qtext">{q.text}</p>
          {q.examiner && (
            <div className="aos-examiner-note">
              <Icon name="alert-triangle" size={15} />
              <span>
                <strong>Examiner note:</strong> {q.examiner}
              </span>
            </div>
          )}
          <SectionTitle>Markscheme</SectionTitle>
          <div className="aos-scheme">
            {(q.scheme.length
              ? q.scheme
              : [{ code: "—", text: "Markscheme not loaded for this question." }]
            ).map((m, i) => (
              <div key={i} className="aos-scheme-row">
                <span className="aos-scheme-code">{m.code}</span>
                <span className="aos-scheme-text">{m.text}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* RIGHT — your response */}
        <Card>
          <SectionTitle>Your response</SectionTitle>
          <div
            className={`aos-upload ${uploaded ? "filled" : ""}`}
            onClick={upload}
          >
            {!uploaded && (
              <>
                <Icon name="cloud-upload" size={26} style={{ color: "var(--text-3)" }} />
                <span>Drag &amp; drop or tap to upload your answer</span>
              </>
            )}
            {uploaded && ocr && (
              <>
                <div className="aos-spinner" />
                <span>OCR processing…</span>
              </>
            )}
            {uploaded && !ocr && (
              <div className="aos-thumb">
                <Icon name="file-check" size={22} style={{ color: "var(--accent)" }} />
                <span>answer_q{q.n}.jpg · OCR complete</span>
              </div>
            )}
          </div>

          <div className="aos-field">
            <label>Marks awarded</label>
            <div className="aos-mark-buttons">
              {Array.from({ length: q.marks + 1 }, (_, i) => i).map((v) => (
                <button
                  key={v}
                  className={`aos-mark-num ${awarded[active] === v ? "sel" : ""}`}
                  onClick={() => {
                    const n = [...awarded];
                    n[active] = v;
                    setAwarded(n);
                  }}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          <div className="aos-field">
            <label>Where did you lose marks?</label>
            <div className="aos-tags">
              {MISTAKES.map((t) => (
                <button
                  key={t}
                  className={`aos-tag ${tags.includes(t) ? "sel" : ""}`}
                  onClick={() => toggleTag(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="aos-field">
            <label>Confidence before marking</label>
            <div className="aos-conf">
              {[1, 2, 3, 4, 5].map((c) => (
                <button
                  key={c}
                  className="aos-conf-dot"
                  style={{
                    background: conf === c ? CONF_COLORS[c - 1] : "transparent",
                    color: conf === c ? "#fff" : CONF_COLORS[c - 1],
                    borderColor: CONF_COLORS[c - 1],
                  }}
                  onClick={() => setConf(c)}
                >
                  {c}
                </button>
              ))}
              <span className="aos-conf-help">
                {conf === 1 ? "guessed" : conf === 5 ? "certain" : ""}
              </span>
            </div>
          </div>

          <div className="aos-field">
            <label>Notes (optional)</label>
            <textarea
              className="aos-textarea"
              rows={2}
              placeholder="Add a note about this question"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>

          <div className="aos-mark-actions">
            <Button variant="primary" icon="arrow-right" onClick={save}>
              Save &amp; next question
            </Button>
            <Button variant="ghost" onClick={skip}>
              Skip for now
            </Button>
          </div>
        </Card>
      </div>

      <div className="aos-mark-sticky">
        <span>
          <strong>{scored}</strong> / {paper.max} marks
        </span>
        <span className="aos-sep">·</span>
        <span>
          Grade <GradeBadge grade={liveGrade} />
        </span>
        <span className="aos-sep">·</span>
        <span>{qs.length - markedN} questions remaining</span>
        <span className="aos-sep">·</span>
        <button className="aos-link" onClick={() => go("questions")}>
          Deep-dive a question →
        </button>
      </div>
    </div>
  );
}

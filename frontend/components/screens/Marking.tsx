"use client";

import { useState, useEffect } from "react";
import { Badge, Button, Card, GradeBadge, Icon, SectionTitle } from "@/components/ui";
import { gradeFromPct } from "@/lib/data";
import { usePaperQuestions, useQuestion } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { Route, SessionParams, ApiQuestion } from "@/lib/types";

const MISTAKES = [
  "Algebra", "Logarithms", "Units", "Wrong method", "Missed step",
  "Rearrangement", "Definition", "Significant figures", "Sign error", "Other",
];
const CONF_COLORS = [
  "var(--danger)", "var(--warn)", "#C9A227", "var(--accent)", "#0E8A5F",
];

function Skeleton({ h }: { h?: number }) {
  return <div className="aos-skeleton" style={{ height: h ?? 18, borderRadius: 4 }} />;
}

export function Marking({
  go,
  session,
}: {
  go: (r: Route, p?: SessionParams) => void;
  session: SessionParams;
}) {
  const { paperId, sessionId } = session;
  const { data: questions, loading: qLoading, error: qError } = usePaperQuestions(paperId ?? null);

  const [awarded, setAwarded] = useState<(number | null)[]>([]);
  const [active, setActive] = useState(0);
  const [tags, setTags] = useState<string[]>([]);
  const [conf, setConf] = useState(3);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Init awarded array when questions load
  useEffect(() => {
    if (questions.length > 0) {
      setAwarded(new Array(questions.length).fill(null));
    }
  }, [questions.length]);

  const q: ApiQuestion | undefined = questions[active];

  // Fetch full detail (markscheme + examiner) for the active question — refetches on change
  const { data: detail, loading: detailLoading } = useQuestion(q?.id ?? null);

  const scored = awarded.reduce<number>((a, v) => a + (v ?? 0), 0);
  const possibleSoFar = awarded.reduce<number>(
    (a, v, i) => a + (v == null ? 0 : (questions[i]?.marks ?? 0)),
    0
  );
  const markedN = awarded.filter((v) => v != null).length;
  const totalMax = questions.reduce((a, q) => a + (q.marks || 0), 0);
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
    if (a === questions[i]?.marks) return "green";
    return "amber";
  };

  const save = async () => {
    if (!q) return;
    const marksAwarded = awarded[active] ?? 0;
    setSaving(true);
    setSaveError(null);
    try {
      if (sessionId) {
        await api.markQuestion(sessionId, q.id, {
          awarded: marksAwarded,
          tags,
          confidence: conf,
          note: note || undefined,
        });
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setSaveError(msg);
      console.error("[marking] save error:", e);
      setSaving(false);
      return; // Do not advance on failure
    }
    setSaving(false);

    // Advance to next unmarked question
    const next = [...awarded];
    if (next[active] == null) next[active] = 0;
    setAwarded(next);
    let n = active + 1;
    while (n < questions.length && next[n] != null) n++;
    if (n < questions.length) {
      setActive(n);
      setTags([]);
      setConf(3);
      setNote("");
    }
  };

  const skip = () => {
    let n = active + 1;
    while (n < questions.length && awarded[n] != null) n++;
    if (n < questions.length) {
      setActive(n);
      setTags([]);
      setConf(3);
      setNote("");
    }
  };

  const toggleTag = (t: string) =>
    setTags((s) => (s.includes(t) ? s.filter((x) => x !== t) : [...s, t]));

  // Loading state
  if (qLoading) {
    return (
      <div className="aos-page">
        <div className="aos-marking-head">
          <div>
            <h1>Loading paper…</h1>
            <p className="aos-page-sub">Fetching questions from database</p>
          </div>
        </div>
        <div className="aos-mark-split">
          <Card><Skeleton h={300} /></Card>
          <Card><Skeleton h={300} /></Card>
        </div>
      </div>
    );
  }

  // No paper error
  if (!paperId) {
    return (
      <div className="aos-page">
        <div className="aos-empty-state" style={{ marginTop: 80 }}>
          <Icon name="file-x" size={32} style={{ color: "var(--text-3)" }} />
          <h2 style={{ marginTop: 16 }}>No paper selected</h2>
          <p className="aos-page-sub">Complete a timed session first, or select a paper from Analytics.</p>
          <Button variant="primary" onClick={() => go("analytics")} style={{ marginTop: 16 }}>
            Browse papers
          </Button>
        </div>
      </div>
    );
  }

  if (qError || questions.length === 0) {
    return (
      <div className="aos-page">
        <div className="aos-alert" style={{ color: "var(--danger)" }}>
          <Icon name="alert-circle" size={16} />
          {qError ?? "No questions found for this paper."}
        </div>
        <Button variant="ghost" onClick={() => go("analytics")} style={{ marginTop: 16 }}>
          ← Back to papers
        </Button>
      </div>
    );
  }

  if (!q) return null;

  const paperLabel = session.paperCode ?? `Paper ${paperId}`;
  const sessionLabel = session.paperSession ?? "";

  return (
    <div className="aos-page">
      <div className="aos-marking-head">
        <div>
          <h1>{paperLabel} · {sessionLabel}</h1>
          <p className="aos-page-sub">
            Marking · {markedN} of {questions.length} questions marked
            {!sessionId && (
              <span style={{ color: "var(--warn)", marginLeft: 8 }}>
                (no session — marks not saved to DB)
              </span>
            )}
          </p>
        </div>
        <div className="aos-marking-score">
          <div className="aos-live-score">
            {scored}
            <span className="aos-live-max"> / {totalMax}</span>
          </div>
          <div className="aos-live-grade">
            <span>Live grade</span>
            <GradeBadge grade={liveGrade} />
            <span className="aos-muted">{pct}%</span>
          </div>
        </div>
      </div>

      <div className="aos-pill-row">
        {questions.map((qq: ApiQuestion, i: number) => {
          const tone = pillTone(i);
          return (
            <button
              key={qq.id}
              className="aos-qpill"
              style={{
                background: PILL_BG[tone],
                color: tone === "grey" ? "var(--text-2)" : "#fff",
                borderColor: tone === "grey" ? "var(--border)" : "transparent",
              }}
              onClick={() => setActive(i)}
            >
              {qq.n}
            </button>
          );
        })}
      </div>

      {saveError && (
        <div className="aos-alert" style={{ color: "var(--danger)", marginBottom: 12 }}>
          <Icon name="alert-circle" size={16} />
          Failed to save: {saveError}
        </div>
      )}

      <div className="aos-mark-split">
        {/* LEFT — question + markscheme */}
        <Card>
          <div className="aos-mark-qhead">
            <span className="aos-mark-qnum">Q{q.n}</span>
            <Badge tone="primary">{q.marks} marks</Badge>
            {q.module_code && <Badge>{q.module_code}</Badge>}
          </div>
          <p className="aos-mark-qtext">
            {(detail?.text ?? q.text) || "Question text not extracted. Check raw PDF."}
          </p>
          {detail?.examiner && (
            <div className="aos-examiner-note">
              <Icon name="alert-triangle" size={15} />
              <span>
                <strong>Examiner note:</strong> {detail.examiner}
              </span>
            </div>
          )}
          <SectionTitle>Markscheme</SectionTitle>
          <div className="aos-scheme">
            {detailLoading ? (
              <Skeleton h={80} />
            ) : detail?.markscheme && detail.markscheme.length > 0 ? (
              detail.markscheme.map((m, i) => (
                <div key={i} className="aos-scheme-row">
                  <span className="aos-scheme-code">{m.code}</span>
                  <span className="aos-scheme-text">{m.text}</span>
                </div>
              ))
            ) : (
              <div className="aos-empty-state">
                <Icon name="file-x" size={16} style={{ color: "var(--text-3)" }} />
                <span>
                  No markscheme extracted for this question yet.
                </span>
              </div>
            )}
          </div>
        </Card>

        {/* RIGHT — your response */}
        <Card>
          <SectionTitle>Your response</SectionTitle>

          <div className="aos-field">
            <label>Marks awarded</label>
            <div className="aos-mark-buttons">
              {Array.from({ length: (q.marks || 0) + 1 }, (_, i) => i).map((v) => (
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
            <Button
              variant="primary"
              icon={saving ? "loader" : "arrow-right"}
              onClick={save}
              disabled={saving || awarded[active] == null}
            >
              {saving ? "Saving…" : "Save & next question"}
            </Button>
            <Button variant="ghost" onClick={skip} disabled={saving}>
              Skip for now
            </Button>
          </div>
        </Card>
      </div>

      <div className="aos-mark-sticky">
        <span>
          <strong>{scored}</strong> / {totalMax} marks
        </span>
        <span className="aos-sep">·</span>
        <span>
          Grade <GradeBadge grade={liveGrade} />
        </span>
        <span className="aos-sep">·</span>
        <span>{questions.length - markedN} questions remaining</span>
        <span className="aos-sep">·</span>
        <button className="aos-link" onClick={() => go("questions")}>
          Deep-dive a question →
        </button>
      </div>
    </div>
  );
}

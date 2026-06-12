"use client";

import { useState, useMemo } from "react";
import { Badge, Button, Card, EmptyState, ErrorState, GradeBadge, Icon, Loading, SectionTitle } from "@/components/ui";
import { gradeFromPct } from "@/lib/data";
import { getPaperQuestions, submitAttempt } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { ApiQuestion, Route } from "@/lib/types";
import type { AppSession } from "@/components/ClientLayout";

const MISTAKES = [
  "Algebra", "Logarithms", "Units", "Wrong method", "Missed step",
  "Rearrangement", "Definition", "Significant figures", "Sign error", "Other",
];
const CONF_COLORS = [
  "var(--danger)", "var(--warn)", "#C9A227", "var(--accent)", "#0E8A5F",
];

export function Marking({ go, session }: { go: (r: Route) => void; session: AppSession }) {
  const paperId = session.paperId;

  if (!paperId) {
    return (
      <div className="aos-page">
        <EmptyState
          icon="checkbox"
          title="No paper selected for marking"
          sub="Start a timed paper first — its questions and markschemes load here."
        />
        <div style={{ marginTop: 14, textAlign: "center" }}>
          <Button variant="primary" icon="player-play" onClick={() => go("timer")}>
            Start a paper
          </Button>
        </div>
      </div>
    );
  }
  return <MarkingInner go={go} session={session} paperId={paperId} />;
}

function MarkingInner({
  go, session, paperId,
}: {
  go: (r: Route) => void;
  session: AppSession;
  paperId: string;
}) {
  const { data, loading, error, retry } = useFetch(() => getPaperQuestions(paperId), [paperId]);

  const qs: ApiQuestion[] = useMemo(
    () => (data?.questions ?? []).filter((q) => q.marks > 0 || (q.question_text ?? "").length > 20),
    [data],
  );

  const [awarded, setAwarded] = useState<Record<string, number | null>>({});
  const [active, setActive] = useState(0);
  const [tags, setTags] = useState<string[]>([]);
  const [conf, setConf] = useState(3);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [lastMastery, setLastMastery] = useState<number | null>(null);

  if (loading) return <div className="aos-page"><Loading label="Loading questions and markschemes…" /></div>;
  if (error || !data) {
    return <div className="aos-page"><ErrorState message={error ?? "Paper not found"} retry={retry} /></div>;
  }
  if (qs.length === 0) {
    return <div className="aos-page"><EmptyState title="No usable questions in this paper" /></div>;
  }

  const q = qs[Math.min(active, qs.length - 1)];
  const maxMarks = qs.reduce((a, x) => a + (x.marks || 0), 0);
  const scored = qs.reduce((a, x) => a + (awarded[x.id] ?? 0), 0);
  const possibleSoFar = qs.reduce((a, x) => a + (awarded[x.id] == null ? 0 : x.marks), 0);
  const markedN = qs.filter((x) => awarded[x.id] != null).length;
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
    const a = awarded[qs[i].id];
    if (i === active) return "blue";
    if (a == null) return "grey";
    if (a === 0) return "red";
    if (a === qs[i].marks) return "green";
    return "amber";
  };

  const resetEntry = () => {
    setTags([]);
    setConf(3);
    setNote("");
    setSaveError(null);
  };

  const save = async () => {
    const marks = awarded[q.id];
    if (marks == null) {
      setSaveError("Select marks awarded before saving.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const result = await submitAttempt({
        session_id: session.sessionId,
        question_id: Number(q.id),
        marks_awarded: marks,
        marks_available: q.marks,
        mistake_types: tags,
        confidence: conf,
        time_seconds: 0,
        notes: note,
      });
      setLastMastery(result.new_mastery);
      let n = active + 1;
      while (n < qs.length && awarded[qs[n].id] != null) n++;
      if (n < qs.length) setActive(n);
      resetEntry();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const skip = () => {
    let n = active + 1;
    while (n < qs.length && awarded[qs[n].id] != null) n++;
    if (n < qs.length) setActive(n);
    resetEntry();
  };

  const toggleTag = (t: string) =>
    setTags((s) => (s.includes(t) ? s.filter((x) => x !== t) : [...s, t]));

  return (
    <div className="aos-page">
      <div className="aos-marking-head">
        <div>
          <h1>{data.paper.full_code} · {data.paper.session}</h1>
          <p className="aos-page-sub">
            Marking · {markedN} of {qs.length} questions marked
            {lastMastery != null && (
              <> · <Badge tone="green">mastery now {Math.round(lastMastery * 100)}%</Badge></>
            )}
          </p>
        </div>
        <div className="aos-marking-score">
          <div className="aos-live-score">
            {scored}<span className="aos-live-max"> / {maxMarks}</span>
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
              key={qq.id}
              className="aos-qpill"
              style={{
                background: PILL_BG[tone],
                color: tone === "grey" ? "var(--text-2)" : "#fff",
                borderColor: tone === "grey" ? "var(--border)" : "transparent",
              }}
              onClick={() => { setActive(i); resetEntry(); }}
            >
              {qq.question_number}
            </button>
          );
        })}
      </div>

      <div className="aos-mark-split">
        {/* LEFT — question + markscheme */}
        <Card>
          <div className="aos-mark-qhead">
            <span className="aos-mark-qnum">Q{q.question_number}</span>
            <Badge tone="primary">{q.marks} marks</Badge>
            {q.topic && q.topic !== "Unknown" && <Badge>{q.topic}</Badge>}
            {q.subtopic && <Badge>{q.subtopic}</Badge>}
          </div>
          <p className="aos-mark-qtext" style={{ whiteSpace: "pre-wrap" }}>
            {(q.question_text ?? "").trim() || "Question text was not extracted for this question."}
          </p>
          <SectionTitle>Markscheme</SectionTitle>
          <div className="aos-scheme">
            {q.markscheme.length === 0 ? (
              <div className="aos-scheme-row">
                <span className="aos-scheme-code">—</span>
                <span className="aos-scheme-text">
                  No markscheme extracted for this question yet.
                </span>
              </div>
            ) : (
              q.markscheme.map((m, i) => (
                <div key={i} className="aos-scheme-row">
                  <span className="aos-scheme-code">{m.code}</span>
                  <span className="aos-scheme-text">
                    {m.text}
                    {m.conditionality && (
                      <span className="aos-muted"> ({m.conditionality})</span>
                    )}
                  </span>
                </div>
              ))
            )}
          </div>
          <div style={{ marginTop: 12 }}>
            <button
              className="aos-link"
              onClick={() => { session.setQuestionId(q.id); go("questions"); }}
            >
              Deep-dive this question →
            </button>
          </div>
        </Card>

        {/* RIGHT — your response */}
        <Card>
          <SectionTitle>Your marking</SectionTitle>

          <div className="aos-field">
            <label>Marks awarded</label>
            <div className="aos-mark-buttons">
              {Array.from({ length: q.marks + 1 }, (_, i) => i).map((v) => (
                <button
                  key={v}
                  className={`aos-mark-num ${awarded[q.id] === v ? "sel" : ""}`}
                  onClick={() => setAwarded((prev) => ({ ...prev, [q.id]: v }))}
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

          {saveError && (
            <div className="aos-alert" style={{ marginBottom: 10 }}>
              <Icon name="alert-triangle" size={15} /> {saveError}
            </div>
          )}

          <div className="aos-mark-actions">
            <Button variant="primary" icon="arrow-right" onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save & next question"}
            </Button>
            <Button variant="ghost" onClick={skip} disabled={saving}>
              Skip for now
            </Button>
          </div>
        </Card>
      </div>

      <div className="aos-mark-sticky">
        <span><strong>{scored}</strong> / {maxMarks} marks</span>
        <span className="aos-sep">·</span>
        <span>Grade <GradeBadge grade={liveGrade} /></span>
        <span className="aos-sep">·</span>
        <span>{qs.length - markedN} questions remaining</span>
      </div>
    </div>
  );
}

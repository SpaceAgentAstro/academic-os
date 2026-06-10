"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Badge, Button, Card, Icon, SectionTitle } from "@/components/ui";
import { usePaperQuestions } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { Route, SessionParams, ApiQuestion } from "@/lib/types";

function fmt(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function mmss(s: number): string {
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

function Skeleton({ h }: { h?: number }) {
  return <div className="aos-skeleton" style={{ height: h ?? 18, borderRadius: 4 }} />;
}

export function Timer({
  go,
  session,
}: {
  go: (r: Route, p?: SessionParams) => void;
  session: SessionParams;
}) {
  const { paperId } = session;
  const { data: questions, loading: qLoading, error: qError } = usePaperQuestions(paperId ?? null);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [qTimes, setQTimes] = useState<number[]>([0]);
  const [running, setRunning] = useState(false);
  const [started, setStarted] = useState(false);
  const [finishing, setFinishing] = useState(false);

  const sessionIdRef = useRef<string | null>(null);
  sessionIdRef.current = sessionId;

  const TARGET = 60 * 60;
  const OFFICIAL = 90 * 60;
  const cur = qTimes.length - 1;

  // Create session when questions load
  useEffect(() => {
    if (!paperId || questions.length === 0 || sessionId) return;
    api.createSession({ paper_id: paperId, target_seconds: TARGET })
      .then((r) => {
        setSessionId(r.id);
        setRunning(true);
        setStarted(true);
      })
      .catch((e) => {
        console.error("[timer] session create error:", e);
        setSessionError(e.message);
        // Still allow timer to run without session persistence
        setRunning(true);
        setStarted(true);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paperId, questions.length]);

  // Timer tick
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setElapsed((e) => e + 1);
      setQTimes((t) => {
        const c = [...t];
        c[c.length - 1] += 1;
        return c;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [running]);

  // Log per-question time on question advance
  const logTime = useCallback(
    (qIdx: number, timeSec: number) => {
      const sid = sessionIdRef.current;
      const q = questions[qIdx];
      if (!sid || !q) return;
      api.logQuestionTime(sid, q.id, { time_seconds: timeSec }).catch(() => {});
    },
    [questions]
  );

  const done = cur;
  const avg = done > 0 ? Math.round(qTimes.slice(0, done).reduce((a, b) => a + b, 0) / done) : 0;
  const overTarget = elapsed > TARGET;
  const overOfficial = elapsed > OFFICIAL;
  const remaining = Math.max(0, OFFICIAL - elapsed);
  const pct = Math.min(100, (elapsed / TARGET) * 100);
  const curAvgDelta = avg > 0 ? qTimes[cur] - avg : 0;
  const overPace = curAvgDelta > 60;

  const pace: [string, string] = overOfficial
    ? ["Over time", "danger"]
    : overTarget
    ? ["At risk", "warn"]
    : ["On pace", "accent"];

  const timerColor = overOfficial ? "var(--danger)" : overTarget ? "var(--warn)" : "var(--text-1)";
  const fillColor = overOfficial ? "var(--danger)" : overTarget ? "var(--warn)" : "var(--primary)";

  const nextQ = async () => {
    logTime(cur, qTimes[cur]);
    if (cur >= questions.length - 1) {
      await finish();
      return;
    }
    setQTimes((t) => [...t, 0]);
  };

  const finish = async () => {
    if (finishing) return;
    setFinishing(true);
    setRunning(false);
    const sid = sessionIdRef.current;
    try {
      if (sid) await api.completeSession(sid);
    } catch (e) {
      console.error("[timer] complete error:", e);
    }
    go("marking", {
      ...session,
      sessionId: sid ?? undefined,
    });
  };

  // beforeunload: fire-and-forget complete
  useEffect(() => {
    const handler = () => {
      const sid = sessionIdRef.current;
      if (sid) {
        navigator.sendBeacon(`/api/sessions/${sid}/complete`, "{}");
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, []);

  // No paper selected
  if (!paperId) {
    return (
      <div className="aos-page">
        <div className="aos-empty-state" style={{ marginTop: 80 }}>
          <Icon name="player-play" size={32} style={{ color: "var(--text-3)" }} />
          <h2 style={{ marginTop: 16 }}>No paper selected</h2>
          <p className="aos-page-sub" style={{ marginTop: 8 }}>
            Go to Analytics → Paper Library and click a paper to start.
          </p>
          <Button variant="primary" onClick={() => go("analytics")} style={{ marginTop: 16 }}>
            Browse papers
          </Button>
        </div>
      </div>
    );
  }

  // Loading questions
  if (qLoading) {
    return (
      <div className="aos-page">
        <div className="aos-page-head">
          <h1>Loading paper…</h1>
        </div>
        <div className="aos-two-col aos-timer-grid">
          <div className="aos-col"><Card><Skeleton h={200} /></Card></div>
          <div className="aos-col"><Card><Skeleton h={300} /></Card></div>
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

  const paperLabel = session.paperCode
    ? `${session.paperCode} — ${session.paperUnit ?? ""} · ${session.paperSession ?? ""}`
    : `Paper ${paperId}`;

  return (
    <div className="aos-page">
      <div className="aos-timer-head">
        <div>
          <h1>{paperLabel}</h1>
          <p className="aos-page-sub">
            {questions.reduce((a, q) => a + (q.marks || 0), 0)} marks ·
            Official 90 min · Target 60 min{" "}
            <Badge tone="primary">two-thirds rule</Badge>
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {sessionError && (
            <span style={{ fontSize: 12, color: "var(--warn)" }}>
              Session not saved
            </span>
          )}
          <Badge tone={started ? "red" : "neutral"}>
            {started ? "● IN PROGRESS" : "READY"}
          </Badge>
        </div>
      </div>

      {overPace && (
        <div className="aos-alert">
          <Icon name="alert-triangle" size={16} />
          You are {mmss(curAvgDelta)} over average pace. Speed up on short questions.
        </div>
      )}

      <div className="aos-two-col aos-timer-grid">
        <div className="aos-col">
          <Card className="aos-timer-block">
            <div className="aos-timer-big" style={{ color: timerColor }}>
              {fmt(elapsed)}
            </div>
            <div className="aos-timer-rem">
              {fmt(remaining)} remaining · target 60:00
            </div>
            <div className="aos-timer-track">
              <div className="aos-timer-fill" style={{ width: `${pct}%`, background: fillColor }} />
              <div className="aos-timer-mark" style={{ left: "66.6%" }} title="Official 90 min" />
            </div>
            <div className="aos-timer-controls">
              <Button
                variant={running ? "ghost" : "primary"}
                icon={running ? "player-pause" : "player-play"}
                onClick={() => setRunning((r) => !r)}
              >
                {running ? "Pause" : "Resume"}
              </Button>
            </div>
          </Card>

          <div className="aos-pace-row">
            <div className="aos-card aos-metric">
              <div className="aos-metric-label">Questions done</div>
              <div className="aos-metric-value">
                {done} <span className="aos-metric-of">of {questions.length}</span>
              </div>
            </div>
            <div className="aos-card aos-metric">
              <div className="aos-metric-label">Avg / question</div>
              <div className="aos-metric-value">{avg > 0 ? mmss(avg) : "—"}</div>
            </div>
            <div className="aos-card aos-metric">
              <div className="aos-metric-label">Pace status</div>
              <div className="aos-metric-value" style={{ color: `var(--${pace[1]})` }}>
                {pace[0]}
              </div>
            </div>
          </div>

          <div className="aos-timer-actions">
            <Button variant="primary" size="lg" icon="arrow-right" onClick={nextQ} disabled={finishing}>
              {cur >= questions.length - 1
                ? "Finish — go to marking"
                : `Done with Q${questions[cur]?.n ?? cur + 1} — next question`}
            </Button>
            <Button variant="ghost" size="lg" onClick={finish} disabled={finishing}>
              Finished paper — go to marking
            </Button>
          </div>
        </div>

        <div className="aos-col">
          <Card pad={false}>
            <SectionTitle>Per-question log</SectionTitle>
            <div className="aos-qlog">
              {questions.map((q: ApiQuestion, i: number) => {
                const state = i < cur ? "done" : i === cur ? "current" : "pending";
                return (
                  <div key={q.id} className={`aos-qlog-row ${state}`}>
                    <span className="aos-qlog-n">Q{q.n}</span>
                    <span className="aos-qlog-marks">{q.marks} marks</span>
                    <span className="aos-qlog-time">
                      {state === "pending" ? "—" : mmss(qTimes[i] ?? 0)}
                    </span>
                    <span className="aos-qlog-status">
                      {state === "done" && (
                        <Icon name="check" size={15} style={{ color: "var(--accent)" }} />
                      )}
                      {state === "current" && <Badge tone="primary">in progress</Badge>}
                      {state === "pending" && <span className="aos-muted">pending</span>}
                    </span>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

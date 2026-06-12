"use client";

import { useState, useEffect } from "react";
import { Badge, Button, Card, Icon, SectionTitle } from "@/components/ui";
import { markingPaper } from "@/lib/data";
import type { Route } from "@/lib/types";

function fmt(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function mmss(s: number): string {
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

export function Timer({ go }: { go: (r: Route) => void }) {
  const paper = markingPaper;
  const qs = paper.questions;
  const TARGET = 60 * 60;
  const OFFICIAL = 90 * 60;

  const seed = [252, 453, 349, 367];
  const [elapsed, setElapsed] = useState(seed.reduce((a, b) => a + b, 0) + 41);
  const [qTimes, setQTimes] = useState<number[]>([...seed, 41]);
  const [running, setRunning] = useState(true);
  const cur = qTimes.length - 1;

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

  const done = cur;
  const avg = done > 0 ? Math.round(qTimes.slice(0, done).reduce((a, b) => a + b, 0) / done) : 0;
  const overTarget = elapsed > TARGET;
  const overOfficial = elapsed > OFFICIAL;
  const remaining = Math.max(0, OFFICIAL - elapsed);
  const pct = Math.min(100, (elapsed / OFFICIAL) * 100);
  const curAvgDelta = qTimes[cur] - avg;
  const overPace = done > 0 && curAvgDelta > 60;

  const pace: [string, string] = overOfficial
    ? ["Over time", "danger"]
    : overTarget
    ? ["At risk", "warn"]
    : ["On pace", "accent"];

  const nextQ = () => {
    if (cur >= qs.length - 1) { go("marking"); return; }
    setQTimes((t) => [...t, 0]);
  };

  const timerColor = overOfficial
    ? "var(--danger)"
    : overTarget
    ? "var(--warn)"
    : "var(--text-1)";

  const fillColor = overOfficial
    ? "var(--danger)"
    : overTarget
    ? "var(--warn)"
    : "var(--primary)";

  return (
    <div className="aos-page">
      <div className="aos-timer-head">
        <div>
          <h1>
            {paper.code} — {paper.unit} · {paper.session}
          </h1>
          <p className="aos-page-sub">
            {paper.max} marks · Official 90 min · Target 60 min{" "}
            <Badge tone="primary">two-thirds rule</Badge>
          </p>
        </div>
        <Badge tone="red">● IN PROGRESS</Badge>
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
              {fmt(remaining)} remaining of 1:30:00 · target 1:00:00
            </div>
            <div className="aos-timer-track">
              <div
                className="aos-timer-fill"
                style={{ width: `${pct}%`, background: fillColor }}
              />
              <div
                className="aos-timer-mark"
                style={{ left: `${(TARGET / OFFICIAL) * 100}%` }}
                title="Target 60 min"
              />
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
                {done} <span className="aos-metric-of">of {qs.length}</span>
              </div>
            </div>
            <div className="aos-card aos-metric">
              <div className="aos-metric-label">Avg / question</div>
              <div className="aos-metric-value">{mmss(avg)}</div>
            </div>
            <div className="aos-card aos-metric">
              <div className="aos-metric-label">Pace status</div>
              <div
                className="aos-metric-value"
                style={{ color: `var(--${pace[1]})` }}
              >
                {pace[0]}
              </div>
            </div>
          </div>

          <div className="aos-timer-actions">
            <Button variant="primary" size="lg" icon="arrow-right" onClick={nextQ}>
              {cur >= qs.length - 1
                ? "Finish — go to marking"
                : `Done with Q${qs[cur].n} — next question`}
            </Button>
            <Button variant="ghost" size="lg" onClick={() => go("marking")}>
              Finished paper — go to marking
            </Button>
          </div>
        </div>

        <div className="aos-col">
          <Card pad={false}>
            <SectionTitle>Per-question log</SectionTitle>
            <div className="aos-qlog">
              {qs.map((q, i) => {
                const state = i < cur ? "done" : i === cur ? "current" : "pending";
                return (
                  <div key={q.n} className={`aos-qlog-row ${state}`}>
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
                      {state === "pending" && (
                        <span className="aos-muted">pending</span>
                      )}
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

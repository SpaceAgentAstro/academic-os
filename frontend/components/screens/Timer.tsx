"use client";

import { useState, useEffect, useMemo, useRef } from "react";
import { Badge, Button, Card, ErrorState, Icon, Loading, SectionTitle } from "@/components/ui";
import { fmtClock, fmtMmss, subjectName } from "@/lib/data";
import { completeSession, createSession, getPaperQuestions, getPapers, logQuestionTime } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { ApiQuestion, Route } from "@/lib/types";
import type { AppSession } from "@/components/ClientLayout";

const SUBJECT_FILTERS = ["all", "physics", "maths", "fmaths", "chemistry", "cs"];

// Official IAL exam length defaults to 90 min; target = two-thirds rule
const OFFICIAL_DEFAULT = 90 * 60;

function PaperPicker({ onPick }: { onPick: (paperId: string) => void }) {
  const [subj, setSubj] = useState("all");
  const [search, setSearch] = useState("");
  const { data: papers, loading, error, retry } = useFetch(
    () => getPapers(subj === "all" ? undefined : subj),
    [subj],
  );

  const filtered = useMemo(() => {
    if (!papers) return [];
    const q = search.trim().toLowerCase();
    return papers
      .filter((p) => p.question_count > 0)
      .filter(
        (p) =>
          !q ||
          p.full_code.toLowerCase().includes(q) ||
          p.unit.toLowerCase().includes(q) ||
          p.session.toLowerCase().includes(q)
      )
      .slice(0, 60);
  }, [papers, search]);

  return (
    <div className="aos-page">
      <div className="aos-page-head">
        <h1>Start a timed paper</h1>
        <p className="aos-page-sub">Pick a real past paper from the question bank</p>
      </div>

      <div className="aos-head-flex" style={{ marginBottom: 14 }}>
        <div className="aos-seg sm">
          {SUBJECT_FILTERS.map((s) => (
            <button key={s} className={subj === s ? "active" : ""} onClick={() => setSubj(s)}>
              {s === "all" ? "All" : subjectName(s)}
            </button>
          ))}
        </div>
        <input
          className="aos-input"
          placeholder="Search code, unit, session…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: 260 }}
        />
      </div>

      {loading && <Loading label="Loading papers…" />}
      {error && <ErrorState message={error} retry={retry} />}
      {!loading && !error && filtered.length === 0 && (
        <Card><span className="aos-muted">No papers match. Ingest PDFs into papers/ first.</span></Card>
      )}
      {!loading && !error && filtered.length > 0 && (
        <Card pad={false}>
          <table className="aos-table">
            <thead>
              <tr>
                <th>Code</th><th>Subject</th><th>Unit</th><th>Session</th><th>Questions</th><th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id}>
                  <td className="aos-td-strong">{p.full_code}</td>
                  <td>{subjectName(p.subject)}</td>
                  <td>{p.unit}</td>
                  <td>{p.session}</td>
                  <td>{p.question_count}</td>
                  <td>
                    <Button size="sm" variant="primary" icon="player-play" onClick={() => onPick(p.id)}>
                      Start
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

function RunningTimer({
  go, session, paperId,
}: {
  go: (r: Route) => void;
  session: AppSession;
  paperId: string;
}) {
  const { data, loading, error, retry } = useFetch(() => getPaperQuestions(paperId), [paperId]);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [qTimes, setQTimes] = useState<number[]>([0]);
  const [running, setRunning] = useState(true);
  const sessionStarted = useRef(false);

  const qs: ApiQuestion[] = useMemo(
    () => (data?.questions ?? []).filter((q) => q.marks > 0 || (q.question_text ?? "").length > 20),
    [data],
  );
  const official = OFFICIAL_DEFAULT;
  const target = Math.round(official * (2 / 3));

  // Create the session once the paper is confirmed to exist
  useEffect(() => {
    if (!data || sessionStarted.current) return;
    sessionStarted.current = true;
    createSession({
      paper_id: Number(paperId),
      official_time_seconds: official,
      target_time_seconds: target,
    })
      .then((r) => session.setSessionId(r.session_id))
      .catch((e: Error) => setSessionError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, paperId]);

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

  if (loading) return <div className="aos-page"><Loading label="Loading paper…" /></div>;
  if (error || !data) {
    return <div className="aos-page"><ErrorState message={error ?? "Paper not found"} retry={retry} /></div>;
  }
  if (sessionError) {
    return <div className="aos-page"><ErrorState message={`Could not start session: ${sessionError}`} /></div>;
  }
  if (qs.length === 0) {
    return (
      <div className="aos-page">
        <ErrorState message="This paper has no usable questions extracted." />
        <Button variant="ghost" onClick={() => session.setPaperId(null)}>Pick another paper</Button>
      </div>
    );
  }

  const cur = qTimes.length - 1;
  const done = cur;
  const avg = done > 0 ? Math.round(qTimes.slice(0, done).reduce((a, b) => a + b, 0) / done) : 0;
  const overTarget = elapsed > target;
  const overOfficial = elapsed > official;
  const remaining = Math.max(0, official - elapsed);
  const pct = Math.min(100, (elapsed / target) * 100);
  const curAvgDelta = qTimes[cur] - avg;
  const overPace = done > 0 && curAvgDelta > 60;

  const pace: [string, string] = overOfficial
    ? ["Over time", "danger"]
    : overTarget
    ? ["At risk", "warn"]
    : ["On pace", "accent"];

  const logCurrent = (status: "complete" | "skipped") => {
    const sid = session.sessionId;
    if (sid == null) return;
    logQuestionTime(sid, qs[cur].id, { time_seconds: qTimes[cur], status }).catch((e) =>
      console.error("Failed to log question time:", e)
    );
  };

  const finish = () => {
    logCurrent("complete");
    const sid = session.sessionId;
    if (sid != null) {
      completeSession(sid, elapsed).catch((e) => console.error("Failed to complete session:", e));
    }
    go("marking");
  };

  const nextQ = () => {
    if (cur >= qs.length - 1) { finish(); return; }
    logCurrent("complete");
    setQTimes((t) => [...t, 0]);
  };

  const timerColor = overOfficial ? "var(--danger)" : overTarget ? "var(--warn)" : "var(--text-1)";
  const fillColor = overOfficial ? "var(--danger)" : overTarget ? "var(--warn)" : "var(--primary)";

  return (
    <div className="aos-page">
      <div className="aos-timer-head">
        <div>
          <h1>{data.paper.full_code} — {data.paper.unit} · {data.paper.session}</h1>
          <p className="aos-page-sub">
            {qs.length} questions · Official {Math.round(official / 60)} min · Target {Math.round(target / 60)} min{" "}
            <Badge tone="primary">two-thirds rule</Badge>
          </p>
        </div>
        <Badge tone="red">● IN PROGRESS</Badge>
      </div>

      {overPace && (
        <div className="aos-alert">
          <Icon name="alert-triangle" size={16} />
          You are {fmtMmss(curAvgDelta)} over average pace on this question.
        </div>
      )}

      <div className="aos-two-col aos-timer-grid">
        <div className="aos-col">
          <Card className="aos-timer-block">
            <div className="aos-timer-big" style={{ color: timerColor }}>{fmtClock(elapsed)}</div>
            <div className="aos-timer-rem">
              {fmtClock(remaining)} remaining · target {Math.round(target / 60)}:00
            </div>
            <div className="aos-timer-track">
              <div className="aos-timer-fill" style={{ width: `${pct}%`, background: fillColor }} />
              <div className="aos-timer-mark" style={{ left: "66.6%" }} title="Official time" />
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
              <div className="aos-metric-value">{fmtMmss(avg)}</div>
            </div>
            <div className="aos-card aos-metric">
              <div className="aos-metric-label">Pace status</div>
              <div className="aos-metric-value" style={{ color: `var(--${pace[1]})` }}>{pace[0]}</div>
            </div>
          </div>

          <div className="aos-timer-actions">
            <Button variant="primary" size="lg" icon="arrow-right" onClick={nextQ}>
              {cur >= qs.length - 1
                ? "Finish — go to marking"
                : `Done with Q${qs[cur].question_number} — next question`}
            </Button>
            <Button variant="ghost" size="lg" onClick={finish}>
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
                  <div key={q.id} className={`aos-qlog-row ${state}`}>
                    <span className="aos-qlog-n">Q{q.question_number}</span>
                    <span className="aos-qlog-marks">{q.marks} marks</span>
                    <span className="aos-qlog-time">
                      {state === "pending" ? "—" : fmtMmss(qTimes[i] ?? 0)}
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

export function Timer({ go, session }: { go: (r: Route) => void; session: AppSession }) {
  if (!session.paperId) {
    return (
      <PaperPicker
        onPick={(id) => {
          session.setSessionId(null);
          session.setPaperId(id);
        }}
      />
    );
  }
  return <RunningTimer go={go} session={session} paperId={session.paperId} />;
}

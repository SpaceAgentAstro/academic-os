"use client";

import { Badge, Button, Card, Icon, MasteryBar, SectionTitle } from "@/components/ui";
import { todayStr } from "@/lib/data";
import { useDashboard, useCoverage } from "@/lib/hooks";
import type { Route, SessionParams } from "@/lib/types";

function Skeleton({ h }: { h?: number }) {
  return <div className="aos-skeleton" style={{ height: h ?? 18, borderRadius: 4 }} />;
}

export function Briefing({ go }: { go: (r: Route, p?: SessionParams) => void }) {
  const { data: dash, loading, error } = useDashboard();
  const coverage = useCoverage();

  const dueReviews = dash.due_reviews;
  const traps = dash.examiner_traps;
  const qod = dash.question_of_day;

  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head">
        <h1>Today&apos;s briefing</h1>
        <p className="aos-page-sub">{todayStr()} · spaced repetition + examiner intelligence</p>
      </div>

      {error && (
        <div className="aos-alert" style={{ color: "var(--danger)" }}>
          <Icon name="alert-circle" size={16} />
          Briefing unavailable: {error}. Check the backend on port 8000.
        </div>
      )}

      <Card pad={false}>
        <SectionTitle>
          <Icon name="refresh" size={15} style={{ marginRight: 6, color: "var(--primary)" }} />
          Revision focus
        </SectionTitle>
        <div className="aos-list">
          {loading ? (
            <div className="aos-due-row"><Skeleton h={40} /></div>
          ) : dueReviews.length === 0 ? (
            <div className="aos-empty-state">
              <Icon name="circle-check" size={20} style={{ color: "var(--accent)" }} />
              <span>No topics due for review. Complete a paper to schedule spaced repetition.</span>
            </div>
          ) : (
            dueReviews.map((r, i) => (
              <div key={i} className="aos-due-row">
                <div className="aos-due-num">{i + 1}</div>
                <div className="aos-due-name">{r.topic}</div>
                <Badge tone={r.overdue ? "red" : "amber"}>{r.status}</Badge>
              </div>
            ))
          )}
        </div>
      </Card>

      <Card>
        <SectionTitle>
          <Icon name="help-circle" size={15} style={{ marginRight: 6, color: "var(--primary)" }} />
          Question of the day
        </SectionTitle>
        {loading ? (
          <Skeleton h={70} />
        ) : qod ? (
          <>
            <div className="aos-qod-meta" style={{ marginTop: 4 }}>
              {qod.topic} · {qod.unit} · {qod.marks} marks ·{" "}
              <Badge tone="red">{qod.difficulty}</Badge>
            </div>
            <p className="aos-briefing-q">{qod.text}</p>
            <Button variant="primary" icon="player-play" onClick={() => go("analytics")}>
              Find this paper
            </Button>
          </>
        ) : (
          <div className="aos-empty-state">
            <Icon name="file-x" size={18} style={{ color: "var(--text-3)" }} />
            <span>No question available yet. Ingest past papers to unlock this.</span>
          </div>
        )}
      </Card>

      <Card pad={false}>
        <SectionTitle>
          <Icon name="binoculars" size={15} style={{ marginRight: 6, color: "var(--primary)" }} />
          Examiner intelligence
        </SectionTitle>
        <div style={{ padding: "0 20px 18px" }}>
          {traps.length === 0 ? (
            <div className="aos-empty-state">
              <Icon name="file-description" size={18} style={{ color: "var(--text-3)" }} />
              <span>Examiner reports not yet extracted. Run the extraction pipeline to unlock this.</span>
            </div>
          ) : (
            <div className="aos-trap-list" style={{ marginTop: 10 }}>
              {traps.slice(0, 4).map((t, i) => (
                <div key={i} className="aos-trap">
                  <Icon name="quote" size={15} style={{ color: "var(--warn)", flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <div className="aos-trap-text">{t.text}</div>
                    {t.topic && <div className="aos-trap-topic">{t.topic}</div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Card pad={false}>
        <SectionTitle>Coverage summary</SectionTitle>
        <div style={{ padding: "0 20px 18px" }}>
          {coverage.length === 0 ? (
            <div className="aos-empty-state">
              <Icon name="database" size={18} style={{ color: "var(--text-3)" }} />
              <span>No coverage data yet.</span>
            </div>
          ) : (
            coverage.map((c) => (
              <div key={c.subject_id} className="aos-cov-row">
                <span className="aos-cov-name">{c.subject}</span>
                <MasteryBar
                  value={c.pct}
                  band={c.pct >= 60 ? "green" : c.pct >= 40 ? "amber" : "red"}
                />
                <span className="aos-cov-meta">
                  {c.attempted} attempted · {c.pct}%
                </span>
              </div>
            ))
          )}
        </div>
      </Card>
    </div>
  );
}

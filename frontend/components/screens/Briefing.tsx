"use client";

import { Badge, Button, Card, ErrorState, Icon, Loading, MasteryBar, SectionTitle } from "@/components/ui";
import { todayStr } from "@/lib/data";
import { getCoverage, getDashboard } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Route } from "@/lib/types";
import type { AppSession } from "@/components/ClientLayout";

export function Briefing({ go, session }: { go: (r: Route) => void; session: AppSession }) {
  const dash = useFetch(getDashboard);
  const coverage = useFetch(getCoverage);

  if (dash.loading) return <div className="aos-page aos-narrow"><Loading label="Building briefing…" /></div>;
  if (dash.error || !dash.data) {
    return (
      <div className="aos-page aos-narrow">
        <ErrorState message={dash.error ?? "No data"} retry={dash.retry} />
      </div>
    );
  }

  const d = dash.data;
  const qod = d.question_of_day;

  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head">
        <h1>Today&apos;s briefing</h1>
        <p className="aos-page-sub">{todayStr()} · spaced repetition + examiner intelligence</p>
      </div>

      <Card pad={false}>
        <SectionTitle>
          <Icon name="refresh" size={15} style={{ marginRight: 6, color: "var(--primary)" }} />
          Revision focus
        </SectionTitle>
        {d.todays_priorities.length === 0 ? (
          <div style={{ padding: "0 20px 18px" }}>
            <span className="aos-muted">Nothing due for review today.</span>
          </div>
        ) : (
          <div className="aos-list">
            {d.todays_priorities.map((r, i) => (
              <div key={i} className="aos-due-row">
                <div className="aos-due-num">{i + 1}</div>
                <div className="aos-due-name">{r.subject} {r.unit} — {r.topic}</div>
                <Badge tone={r.days_overdue > 0 ? "red" : "amber"}>
                  {r.days_overdue > 0 ? `Overdue ${r.days_overdue}d` : "Due today"}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </Card>

      {qod && (
        <Card>
          <SectionTitle>
            <Icon name="help-circle" size={15} style={{ marginRight: 6, color: "var(--primary)" }} />
            Question of the day
          </SectionTitle>
          <div className="aos-qod-meta" style={{ marginTop: 4 }}>
            {[qod.topic, qod.unit].filter(Boolean).join(" · ")} · {qod.marks} marks ·{" "}
            <Badge tone="red">{qod.difficulty}</Badge>
          </div>
          <p className="aos-briefing-q" style={{ whiteSpace: "pre-wrap" }}>{qod.text}</p>
          <Button
            variant="primary"
            icon="player-play"
            onClick={() => { session.setQuestionId(qod.id); go("questions"); }}
          >
            Review this question
          </Button>
        </Card>
      )}

      <Card pad={false}>
        <SectionTitle>
          <Icon name="binoculars" size={15} style={{ marginRight: 6, color: "var(--primary)" }} />
          Examiner intelligence
        </SectionTitle>
        <div style={{ padding: "0 20px 18px" }}>
          {d.examiner_traps.length === 0 ? (
            <span className="aos-muted">No examiner reports ingested yet.</span>
          ) : (
            <div className="aos-trap-list" style={{ marginTop: 10 }}>
              {d.examiner_traps.slice(0, 3).map((t, i) => (
                <div key={i} className="aos-trap">
                  <Icon name="quote" size={15} style={{ color: "var(--warn)", flexShrink: 0, marginTop: 2 }} />
                  <div>
                    <div className="aos-trap-text">&ldquo;{t.text}&rdquo;</div>
                    <div className="aos-trap-topic">
                      {[t.subject, t.topic].filter(Boolean).join(" · ")} · seen {t.freq}×
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Card pad={false}>
        <SectionTitle
          action={
            d.streak > 0 ? <Badge tone="green">{d.streak} day streak</Badge> : undefined
          }
        >
          Coverage summary
        </SectionTitle>
        <div style={{ padding: "0 20px 18px" }}>
          {coverage.loading && <span className="aos-muted">Loading coverage…</span>}
          {coverage.error && <span className="aos-muted">Coverage unavailable.</span>}
          {(coverage.data ?? []).map((c) => (
            <div key={c.subject} className="aos-cov-row">
              <span className="aos-cov-name">{c.subject}</span>
              <MasteryBar
                value={c.pct}
                band={c.pct >= 60 ? "green" : c.pct >= 40 ? "amber" : "red"}
              />
              <span className="aos-cov-meta">
                {c.attempted} of {c.total_questions.toLocaleString()} attempted · {c.pct}%
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

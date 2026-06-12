"use client";

import { Badge, Button, Card, Dot, EmptyState, ErrorState, GradeBadge, Icon, Loading, Metric, SectionTitle } from "@/components/ui";
import { bandColor, masteryBand, todayStr } from "@/lib/data";
import { getDashboard } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Route } from "@/lib/types";

export function Home({ go }: { go: (r: Route) => void }) {
  const { data, loading, error, retry } = useFetch(getDashboard);

  if (loading) return <div className="aos-page"><Loading label="Loading dashboard…" /></div>;
  if (error || !data) {
    return (
      <div className="aos-page">
        <ErrorState message="Could not load dashboard data. Is the backend running on port 8000?" retry={retry} />
      </div>
    );
  }

  const d = data;
  const dueCount = d.todays_priorities.length;
  const completedPapers = d.recent_papers.filter((p) => p.pct != null);
  const avgScore = completedPapers.length
    ? Math.round(completedPapers.reduce((a, p) => a + (p.pct ?? 0), 0) / completedPapers.length)
    : null;
  const bestPrediction = d.predicted_grades.length
    ? d.predicted_grades.reduce((a, b) => (b.attempt_count > a.attempt_count ? b : a))
    : null;
  const qod = d.question_of_day;

  return (
    <div className="aos-page">
      <div className="aos-page-head">
        <h1>Good morning, Mouad.</h1>
        <p className="aos-page-sub">
          {todayStr()} · {dueCount} topic{dueCount === 1 ? "" : "s"} due for review
        </p>
      </div>

      <div className="aos-metric-row">
        <Metric
          label="Predicted grade"
          value={bestPrediction ? bestPrediction.predicted : "—"}
          sub={bestPrediction ? `${bestPrediction.subject} · ${bestPrediction.confidence} confidence` : "No attempts yet"}
          accent="var(--accent)"
          icon="award"
        />
        <Metric
          label="Papers completed"
          value={completedPapers.length || "0"}
          sub={completedPapers.length ? "with marked scores" : "Start your first paper"}
          icon="pencil"
        />
        <Metric
          label="Average score"
          value={avgScore != null ? `${avgScore}%` : "—"}
          sub={avgScore != null ? `Across ${completedPapers.length} marked papers` : "No marked papers yet"}
          icon="percentage"
        />
        <Metric
          label="Study streak"
          value={`${d.streak} day${d.streak === 1 ? "" : "s"}`}
          sub={d.streak === 0 ? "Start a session today" : "Keep it going"}
          icon="flame"
        />
      </div>

      <div className="aos-two-col">
        {/* LEFT */}
        <div className="aos-col">
          <Card pad={false}>
            <SectionTitle action={dueCount > 0 ? <Badge tone="amber">{dueCount} due</Badge> : undefined}>
              Today&apos;s priorities
            </SectionTitle>
            {d.todays_priorities.length === 0 ? (
              <div style={{ padding: "0 20px 18px" }}>
                <span className="aos-muted">Nothing due for review today.</span>
              </div>
            ) : (
              <div className="aos-list">
                {d.todays_priorities.map((p, i) => (
                  <div key={`${p.topic}-${i}`} className="aos-priority">
                    <div className="aos-priority-rank">{i + 1}</div>
                    <div className="aos-priority-body">
                      <div className="aos-priority-name">
                        <Dot level={p.mastery < 0.4 ? "high" : p.mastery < 0.7 ? "med" : "low"} />
                        {p.subject} {p.unit} — {p.topic}
                      </div>
                      <Badge tone={p.days_overdue > 0 ? "red" : "amber"}>
                        {p.days_overdue > 0
                          ? `Overdue ${p.days_overdue}d · mastery ${Math.round(p.mastery * 100)}%`
                          : `Due today · mastery ${Math.round(p.mastery * 100)}%`}
                      </Badge>
                    </div>
                    <Button size="sm" variant="primary" onClick={() => go("timer")}>
                      Practise now
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card pad={false}>
            <SectionTitle
              action={
                <button className="aos-link" onClick={() => go("analytics")}>
                  All papers →
                </button>
              }
            >
              Recent papers
            </SectionTitle>
            {d.recent_papers.length === 0 ? (
              <div style={{ padding: "0 20px 18px" }}>
                <span className="aos-muted">No attempts yet. Start your first paper.</span>
              </div>
            ) : (
              <div className="aos-list">
                {d.recent_papers.slice(0, 3).map((p) => {
                  const over =
                    p.time_seconds != null && p.target_seconds != null && p.target_seconds > 0 &&
                    p.time_seconds > p.target_seconds;
                  return (
                    <div key={p.session_id} className="aos-paper-row" onClick={() => go("marking")}>
                      <div>
                        <div className="aos-paper-code">{p.code} {p.session}</div>
                        <div className="aos-paper-meta">
                          {p.score != null ? `${p.score}/${p.max}` : "Not marked yet"} ·{" "}
                          {new Date(p.started_at).toLocaleDateString("en-GB")}
                        </div>
                      </div>
                      <div className="aos-paper-stats">
                        {p.time_seconds != null && (
                          <span className={over ? "aos-time-over" : "aos-time-ok"}>
                            {Math.round(p.time_seconds / 60)} min
                            {p.target_seconds != null && p.target_seconds > 0 && (
                              <span className="aos-target"> / {Math.round(p.target_seconds / 60)}</span>
                            )}
                          </span>
                        )}
                        {p.grade && <GradeBadge grade={p.grade} />}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        {/* RIGHT */}
        <div className="aos-col">
          <Card pad={false}>
            <SectionTitle>Mastery heatmap</SectionTitle>
            {d.subject_mastery.length === 0 ? (
              <div style={{ padding: "0 20px 18px" }}>
                <span className="aos-muted">No syllabus data. Seed progress.db first.</span>
              </div>
            ) : (
              <>
                <div className="aos-heatmap">
                  {d.subject_mastery.map((s) => (
                    <div key={s.subject_id} className="aos-heat-row" onClick={() => go("subjects")}>
                      <div className="aos-heat-name">{s.subject}</div>
                      <div className="aos-heat-track">
                        {s.units.map((u) => (
                          <div
                            key={u.code}
                            className="aos-heat-seg"
                            style={{
                              flexGrow: Math.max(1, u.topic_count),
                              background: bandColor(masteryBand(u.mastery)),
                            }}
                            title={`${u.code} · mastery ${u.mastery}% · ${u.topic_count} topics`}
                          />
                        ))}
                      </div>
                      <div className="aos-heat-pct">{Math.round(s.mastery_pct)}%</div>
                    </div>
                  ))}
                </div>
                <div className="aos-heat-legend">
                  <span><i style={{ background: "var(--accent)" }} />&gt;80%</span>
                  <span><i style={{ background: "var(--warn)" }} />50–80%</span>
                  <span><i style={{ background: "var(--danger)" }} />&lt;50%</span>
                </div>
              </>
            )}
          </Card>

          <Card pad={false}>
            <SectionTitle
              action={
                <button className="aos-link" onClick={() => go("weaknesses")}>
                  Library →
                </button>
              }
            >
              Examiner traps
            </SectionTitle>
            {d.examiner_traps.length === 0 ? (
              <div style={{ padding: "0 20px 18px" }}>
                <span className="aos-muted">No examiner data ingested yet.</span>
              </div>
            ) : (
              <div className="aos-trap-list">
                {d.examiner_traps.slice(0, 3).map((t, i) => (
                  <div key={i} className="aos-trap">
                    <Icon
                      name="alert-triangle"
                      size={15}
                      style={{ color: "var(--warn)", flexShrink: 0, marginTop: 2 }}
                    />
                    <div>
                      <div className="aos-trap-text">{t.text}</div>
                      <div className="aos-trap-topic">
                        {[t.subject, t.topic].filter(Boolean).join(" · ")} · seen {t.freq}×
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {qod ? (
            <Card className="aos-qod">
              <div className="aos-qod-tag">
                <Icon name="bulb" size={14} /> Question of the day
              </div>
              <div className="aos-qod-meta">
                {[qod.topic, qod.unit].filter(Boolean).join(" · ")} · {qod.marks} marks · {qod.difficulty}
              </div>
              <p className="aos-qod-text">{qod.text}</p>
              <Button variant="onnavy" icon="arrow-right" onClick={() => go("briefing")}>
                View full briefing
              </Button>
            </Card>
          ) : (
            <EmptyState title="No question of the day" sub="Ingest past papers to enable daily questions." />
          )}
        </div>
      </div>
    </div>
  );
}

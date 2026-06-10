"use client";

import { Badge, Button, Card, Dot, GradeBadge, Icon, Metric, SectionTitle } from "@/components/ui";
import { bandColor, gradeFromPct, masteryBand, todayStr } from "@/lib/data";
import { useDashboard, useCoverage, useRawPapers } from "@/lib/hooks";
import type { Route, SessionParams } from "@/lib/types";

function Skeleton({ w, h }: { w?: string; h?: number }) {
  return (
    <div
      className="aos-skeleton"
      style={{ width: w ?? "100%", height: h ?? 18, borderRadius: 4 }}
    />
  );
}

export function Home({
  go,
  greeting,
}: {
  go: (r: Route, p?: SessionParams) => void;
  greeting?: string;
}) {
  const { data: dash, loading: dashLoading, error: dashError } = useDashboard();
  const coverage = useCoverage();
  const { data: papers, loading: papersLoading } = useRawPapers();

  const metrics = dash.metrics;
  const dueReviews = dash.due_reviews;
  const traps = dash.examiner_traps;
  const qod = dash.question_of_day;

  return (
    <div className="aos-page">
      <div className="aos-page-head">
        <h1>{greeting ?? "Good morning, Mouad Maamma."}</h1>
        <p className="aos-page-sub">
          {todayStr()}
          {dueReviews.length > 0 && ` · ${dueReviews.length} topic${dueReviews.length > 1 ? "s" : ""} due for review`}
        </p>
      </div>

      {dashError && (
        <div className="aos-alert" style={{ color: "var(--danger)" }}>
          <Icon name="alert-circle" size={16} />
          Dashboard error: {dashError}. Check that the backend is running on port 8000.
        </div>
      )}

      <div className="aos-metric-row">
        {dashLoading ? (
          <>
            <div className="aos-card aos-metric"><Skeleton h={40} /></div>
            <div className="aos-card aos-metric"><Skeleton h={40} /></div>
            <div className="aos-card aos-metric"><Skeleton h={40} /></div>
            <div className="aos-card aos-metric"><Skeleton h={40} /></div>
          </>
        ) : (
          <>
            <Metric
              label="Questions attempted"
              value={metrics.total_questions_attempted.toLocaleString()}
              sub={metrics.sessions > 0 ? `Across ${metrics.sessions} sessions` : "Start your first paper"}
              icon="pencil"
            />
            <Metric
              label="Average score"
              value={metrics.avg_score > 0 ? `${metrics.avg_score.toFixed(1)}%` : "—"}
              sub={metrics.sessions > 0 ? "All sessions" : "No data yet"}
              accent={metrics.avg_score >= 70 ? "var(--accent)" : metrics.avg_score > 0 ? "var(--warn)" : undefined}
              icon="percentage"
            />
            <Metric
              label="Sessions"
              value={String(metrics.sessions)}
              sub={metrics.sessions === 0 ? "No sessions yet" : "Papers attempted"}
              icon="files"
            />
            <Metric
              label="Due reviews"
              value={String(dueReviews.length)}
              sub={dueReviews.length === 0 ? "All caught up" : "Topics to review"}
              icon="clock"
            />
          </>
        )}
      </div>

      <div className="aos-two-col">
        {/* LEFT */}
        <div className="aos-col">
          <Card pad={false}>
            <SectionTitle
              action={dueReviews.length > 0 ? <Badge tone="amber">{dueReviews.length} due</Badge> : undefined}
            >
              Today&apos;s priorities
            </SectionTitle>
            <div className="aos-list">
              {dashLoading ? (
                [0, 1, 2].map((i) => (
                  <div key={i} className="aos-priority">
                    <Skeleton h={48} />
                  </div>
                ))
              ) : dueReviews.length === 0 ? (
                <div className="aos-empty-state">
                  <Icon name="circle-check" size={20} style={{ color: "var(--accent)" }} />
                  <span>
                    {metrics.sessions === 0
                      ? "Start your first paper to populate your revision schedule."
                      : "No topics due for review today."}
                  </span>
                </div>
              ) : (
                dueReviews.slice(0, 3).map((p, i) => (
                  <div key={i} className="aos-priority">
                    <div className="aos-priority-rank">{i + 1}</div>
                    <div className="aos-priority-body">
                      <div className="aos-priority-name">
                        <Dot level={p.overdue ? "high" : "med"} />
                        {p.topic}
                      </div>
                      <Badge tone={p.overdue ? "red" : "amber"}>{p.status}</Badge>
                    </div>
                    <Button size="sm" variant="primary" onClick={() => go("booklets")}>
                      Study now
                    </Button>
                  </div>
                ))
              )}
            </div>
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
            <div className="aos-list">
              {papersLoading ? (
                [0, 1, 2].map((i) => (
                  <div key={i} className="aos-paper-row"><Skeleton h={42} /></div>
                ))
              ) : papers.filter((p) => p.score !== null).length === 0 ? (
                <div className="aos-empty-state">
                  <Icon name="file-x" size={20} style={{ color: "var(--text-3)" }} />
                  <span>No sessions yet. Start your first paper to see your performance here.</span>
                </div>
              ) : (
                papers
                  .filter((p) => p.score !== null)
                  .slice(0, 3)
                  .map((p) => {
                    const pct = p.score != null && p.max ? Math.round((p.score / p.max) * 100) : 0;
                    const over = p.time != null && p.target != null && p.time > p.target;
                    return (
                      <div
                        key={p.id}
                        className="aos-paper-row"
                        onClick={() => go("marking", { paperId: p.id })}
                        style={{ cursor: "pointer" }}
                      >
                        <div>
                          <div className="aos-paper-code">{p.code} {p.session}</div>
                          <div className="aos-paper-meta">
                            {p.score}/{p.max} · {p.days_ago} days ago
                          </div>
                        </div>
                        <div className="aos-paper-stats">
                          {p.time != null && (
                            <span className={over ? "aos-time-over" : "aos-time-ok"}>
                              {p.time} min
                              {p.target != null && (
                                <span className="aos-target"> / {p.target}</span>
                              )}
                            </span>
                          )}
                          <GradeBadge grade={gradeFromPct(pct)} />
                        </div>
                      </div>
                    );
                  })
              )}
            </div>
          </Card>
        </div>

        {/* RIGHT */}
        <div className="aos-col">
          <Card pad={false}>
            <SectionTitle>Coverage by subject</SectionTitle>
            <div className="aos-heatmap">
              {coverage.length === 0 ? (
                <div className="aos-empty-state">
                  <Icon name="database" size={20} style={{ color: "var(--text-3)" }} />
                  <span>Syllabus not yet seeded. Run the setup to begin tracking your progress.</span>
                </div>
              ) : (
                coverage.map((c) => {
                  const pct = c.pct;
                  const band = masteryBand(pct);
                  return (
                    <div
                      key={c.subject_id}
                      className="aos-heat-row"
                      onClick={() => go("subjects")}
                      style={{ cursor: "pointer" }}
                    >
                      <div className="aos-heat-name">{c.subject}</div>
                      <div className="aos-heat-track">
                        <div
                          className="aos-heat-seg"
                          style={{
                            flexGrow: c.total_questions || 1,
                            background: bandColor(band),
                            opacity: pct > 0 ? 1 : 0.25,
                          }}
                          title={`${c.attempted} of ${c.total_questions} questions attempted`}
                        />
                      </div>
                      <div className="aos-heat-pct">{pct}%</div>
                    </div>
                  );
                })
              )}
            </div>
            <div className="aos-heat-legend">
              <span><i style={{ background: "var(--accent)" }} />&gt;80%</span>
              <span><i style={{ background: "var(--warn)" }} />50–80%</span>
              <span><i style={{ background: "var(--danger)" }} />&lt;50%</span>
            </div>
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
            <div className="aos-trap-list">
              {traps.length === 0 ? (
                <div className="aos-empty-state">
                  <Icon name="file-description" size={20} style={{ color: "var(--text-3)" }} />
                  <span>
                    Examiner reports not yet extracted. Run the extraction pipeline to unlock this intelligence.
                  </span>
                </div>
              ) : (
                traps.slice(0, 3).map((t, i) => (
                  <div key={i} className="aos-trap">
                    <Icon name="alert-triangle" size={15} style={{ color: "var(--warn)", flexShrink: 0, marginTop: 2 }} />
                    <div>
                      <div className="aos-trap-text">{t.text}</div>
                      <div className="aos-trap-topic">
                        {t.topic} · {t.freq} report{t.freq > 1 ? "s" : ""}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card className="aos-qod">
            <div className="aos-qod-tag">
              <Icon name="bulb" size={14} /> Question of the day
            </div>
            {dashLoading ? (
              <Skeleton h={60} />
            ) : qod ? (
              <>
                <div className="aos-qod-meta">
                  {qod.topic} · {qod.unit} · {qod.marks} marks
                </div>
                <p className="aos-qod-text">{qod.text}</p>
                <Button variant="onnavy" icon="arrow-right" onClick={() => go("briefing")}>
                  View full briefing
                </Button>
              </>
            ) : (
              <div className="aos-empty-state">
                <span>No question available yet. Ingest past papers to unlock this feature.</span>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

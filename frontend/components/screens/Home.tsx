"use client";

import { Badge, Button, Card, Dot, GradeBadge, Icon, Metric, SectionTitle } from "@/components/ui";
import {
  bandColor, dueReviews, gradeFromPct, masteryBand, papers, subjects,
  todaysPriorities, examinerTraps, questionOfDay, todayStr,
} from "@/lib/data";
import type { Route } from "@/lib/types";

export function Home({ go, greeting }: { go: (r: Route) => void; greeting?: string }) {
  const avgPct = Math.round(
    papers.reduce((a, p) => a + (p.score / p.max) * 100, 0) / papers.length
  );
  return (
    <div className="aos-page">
      <div className="aos-page-head">
        <h1>{greeting ?? "Good morning, Mouad Maamma."}</h1>
        <p className="aos-page-sub">
          {todayStr()} · {dueReviews.length} topics due for review · Physics Unit 5 exam in 14 days
        </p>
      </div>

      <div className="aos-metric-row">
        <Metric label="Predicted grade" value="A*" sub="Confidence 84%" accent="var(--accent)" icon="award" />
        <Metric label="Questions this week" value="47" sub="+12 vs last week" icon="pencil" />
        <Metric label="Average score" value={`${avgPct}%`} sub={`Across ${papers.length} papers`} icon="percentage" />
        <Metric label="Study streak" value="9 days" sub="Personal best: 14" icon="flame" />
      </div>

      <div className="aos-two-col">
        {/* LEFT */}
        <div className="aos-col">
          <Card pad={false}>
            <SectionTitle action={<Badge tone="amber">{todaysPriorities.length} due</Badge>}>
              Today&apos;s priorities
            </SectionTitle>
            <div className="aos-list">
              {todaysPriorities.map((p, i) => (
                <div key={i} className="aos-priority">
                  <div className="aos-priority-rank">{i + 1}</div>
                  <div className="aos-priority-body">
                    <div className="aos-priority-name">
                      <Dot level={p.difficulty} />
                      {p.topic}
                    </div>
                    <Badge tone={p.difficulty === "high" ? "red" : "amber"}>{p.reason}</Badge>
                  </div>
                  <Button size="sm" variant="primary" onClick={() => go("booklets")}>
                    Study now
                  </Button>
                </div>
              ))}
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
              {papers.slice(0, 3).map((p) => {
                const pct = Math.round((p.score / p.max) * 100);
                const over = p.time > p.target;
                return (
                  <div key={p.id} className="aos-paper-row" onClick={() => go("marking")}>
                    <div>
                      <div className="aos-paper-code">
                        {p.code} {p.session}
                      </div>
                      <div className="aos-paper-meta">
                        {p.score}/{p.max} · {p.daysAgo} days ago
                      </div>
                    </div>
                    <div className="aos-paper-stats">
                      <span className={over ? "aos-time-over" : "aos-time-ok"}>
                        {p.time} min
                        <span className="aos-target"> / {p.target}</span>
                      </span>
                      <GradeBadge grade={gradeFromPct(pct)} />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* RIGHT */}
        <div className="aos-col">
          <Card pad={false}>
            <SectionTitle>Mastery heatmap</SectionTitle>
            <div className="aos-heatmap">
              {subjects.map((s) => {
                const totalQ = s.units.reduce((a, u) => a + u.questions, 0);
                const avg = Math.round(
                  s.units.reduce((a, u) => a + u.mastery * u.questions, 0) / totalQ
                );
                return (
                  <div key={s.id} className="aos-heat-row" onClick={() => go("subjects")}>
                    <div className="aos-heat-name">{s.name}</div>
                    <div className="aos-heat-track">
                      {s.units.map((u) => (
                        <div
                          key={u.code}
                          className="aos-heat-seg"
                          style={{
                            flexGrow: u.questions,
                            background: bandColor(masteryBand(u.mastery)),
                          }}
                          title={`${u.code} ${u.name} · ${u.mastery}%`}
                        />
                      ))}
                    </div>
                    <div className="aos-heat-pct">{avg}%</div>
                  </div>
                );
              })}
            </div>
            <div className="aos-heat-legend">
              <span>
                <i style={{ background: "var(--accent)" }} />≥80%
              </span>
              <span>
                <i style={{ background: "var(--warn)" }} />50–79%
              </span>
              <span>
                <i style={{ background: "var(--danger)" }} />&lt;50%
              </span>
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
              Upcoming examiner traps
            </SectionTitle>
            <div className="aos-trap-list">
              {examinerTraps.slice(0, 3).map((t, i) => (
                <div key={i} className="aos-trap">
                  <Icon
                    name="alert-triangle"
                    size={15}
                    style={{ color: "var(--warn)", flexShrink: 0, marginTop: 2 }}
                  />
                  <div>
                    <div className="aos-trap-text">{t.text}</div>
                    <div className="aos-trap-topic">
                      {t.topic} · {t.freq} report{t.freq > 1 ? "s" : ""}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="aos-qod">
            <div className="aos-qod-tag">
              <Icon name="bulb" size={14} /> Question of the day
            </div>
            <div className="aos-qod-meta">
              {questionOfDay.topic} · {questionOfDay.unit} · {questionOfDay.marks} marks
            </div>
            <p className="aos-qod-text">{questionOfDay.text}</p>
            <Button variant="onnavy" icon="arrow-right" onClick={() => go("briefing")}>
              View full briefing
            </Button>
          </Card>
        </div>
      </div>
    </div>
  );
}

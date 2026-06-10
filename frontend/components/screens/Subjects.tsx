"use client";

import { useState } from "react";
import { Button, Card, GradeBadge, Icon, MasteryBar, Metric, SectionTitle } from "@/components/ui";
import { bandColor, gradeFromPct, masteryBand } from "@/lib/data";
import { useSubject } from "@/lib/hooks";
import type { Route, SessionParams } from "@/lib/types";

const TABS: { id: string; name: string }[] = [
  { id: "maths", name: "Mathematics" },
  { id: "fmaths", name: "Further Maths" },
  { id: "physics", name: "Physics" },
  { id: "chemistry", name: "Chemistry" },
  { id: "cs", name: "Computer Science" },
];

function Skeleton({ h }: { h?: number }) {
  return <div className="aos-skeleton" style={{ height: h ?? 18, borderRadius: 4 }} />;
}

export function Subjects({ go }: { go: (r: Route, p?: SessionParams) => void }) {
  const [active, setActive] = useState("physics");
  const { data: s, loading } = useSubject(active);

  // Subject-level average mastery across units (real, from spec-point completion)
  const avgMastery =
    s.units.length > 0
      ? Math.round(s.units.reduce((a, u) => a + u.mastery, 0) / s.units.length)
      : 0;

  return (
    <div className="aos-page">
      <div className="aos-tabbar">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`aos-tab ${active === tab.id ? "active" : ""}`}
            onClick={() => setActive(tab.id)}
          >
            {tab.name}
          </button>
        ))}
      </div>

      <div className="aos-subj-head">
        <div>
          <h1>{TABS.find((t) => t.id === active)?.name ?? active}</h1>
          <p className="aos-page-sub">Pearson Edexcel IAL · live mastery from your attempts</p>
        </div>
        <div className="aos-subj-grades">
          <div className="aos-grade-block">
            <span>Mastery grade</span>
            <GradeBadge grade={gradeFromPct(avgMastery)} />
          </div>
          <div className="aos-grade-block">
            <span>Avg mastery</span>
            <strong>{avgMastery}%</strong>
          </div>
        </div>
      </div>

      <div className="aos-metric-row aos-three">
        <Metric label="Papers available" value={String(s.totals.papers)} icon="files" />
        <Metric label="Questions in bank" value={s.totals.questions.toLocaleString()} icon="pencil" />
        <Metric label="Sessions completed" value={String(s.totals.sessions)} icon="checkbox" />
      </div>

      <SectionTitle>Units</SectionTitle>
      {loading ? (
        <div className="aos-unit-grid">
          {[0, 1, 2].map((i) => <Card key={i}><Skeleton h={80} /></Card>)}
        </div>
      ) : s.units.length === 0 ? (
        <Card>
          <div className="aos-empty-state" style={{ padding: 24 }}>
            <Icon name="database" size={18} style={{ color: "var(--text-3)" }} />
            <span>Syllabus not yet seeded for this subject.</span>
          </div>
        </Card>
      ) : (
        <div className="aos-unit-grid">
          {s.units.map((u) => {
            const band = masteryBand(u.mastery);
            return (
              <div key={u.code} className="aos-unit-card">
                <div className="aos-unit-top">
                  <div>
                    <div className="aos-unit-code">{u.code}</div>
                    <div className="aos-unit-name">{u.name}</div>
                  </div>
                  <div className="aos-unit-pct" style={{ color: bandColor(band) }}>
                    {u.mastery}%
                  </div>
                </div>
                <MasteryBar value={u.mastery} band={band} height={6} />
                <div className="aos-unit-foot">
                  <span>{u.questions} questions · {u.spec_points} spec points</span>
                  {u.confidence > 0 && (
                    <span className="aos-muted">conf {u.confidence}/5</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <SectionTitle>Recent attempts</SectionTitle>
      <Card pad={false}>
        {s.recent_attempts.length === 0 ? (
          <div className="aos-empty-state" style={{ padding: 24, flexDirection: "column", gap: 12 }}>
            <Icon name="file-x" size={18} style={{ color: "var(--text-3)" }} />
            <span>No attempts for this subject yet.</span>
            <Button variant="primary" size="sm" icon="player-play" onClick={() => go("analytics")}>
              Browse papers
            </Button>
          </div>
        ) : (
          <table className="aos-table">
            <thead>
              <tr>
                <th>Unit</th>
                <th>Date</th>
                <th>Score</th>
                <th>Grade</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {s.recent_attempts.map((a) => (
                <tr key={a.id}>
                  <td className="aos-td-strong">{a.unit}</td>
                  <td>{(a.started_at || "").slice(0, 10)}</td>
                  <td>
                    {a.score ?? 0}/{a.max ?? 0}{" "}
                    <span className="aos-muted">({a.pct}%)</span>
                  </td>
                  <td><GradeBadge grade={gradeFromPct(a.pct)} /></td>
                  <td>{a.minutes} min</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}

"use client";

import { useState } from "react";
import { Badge, Button, Card, Icon, SectionTitle } from "@/components/ui";
import { bandColor, confidenceTraps, examinerTraps, masteryBand, subjectById, weaknesses } from "@/lib/data";
import type { Route } from "@/lib/types";

export function Weaknesses({ go }: { go: (r: Route) => void }) {
  const [subj, setSubj] = useState("all");
  const [sortKey, setSortKey] = useState<"lost" | "avg" | "attempts">("lost");
  const primary = weaknesses[0];
  const maxOcc = Math.max(...primary.breakdown.map((b) => b.n));

  let rows = weaknesses.filter((w) => subj === "all" || w.subject === subj);
  rows = [...rows].sort((a, b) =>
    sortKey === "lost" ? b.lost - a.lost : sortKey === "avg" ? a.avg - b.avg : b.attempts - a.attempts
  );

  const trendIcon = (t: string): [string, string] =>
    t === "up"
      ? ["trending-up", "var(--accent)"]
      : t === "down"
      ? ["trending-down", "var(--danger)"]
      : ["minus", "var(--text-3)"];

  return (
    <div className="aos-page">
      <div className="aos-page-head">
        <h1>Where your marks are leaking</h1>
        <p className="aos-page-sub">
          Ranked by marks lost · pulled from your attempt history and examiner reports
        </p>
      </div>

      {/* primary weakness */}
      <Card className="aos-primary-weak">
        <div className="aos-pw-flag">
          <Icon name="alert-triangle" size={15} /> Most critical weakness
        </div>
        <div className="aos-pw-grid">
          <div>
            <div className="aos-pw-path">
              {subjectById(primary.subject).name} → {primary.unit} →{" "}
              <strong>{primary.topic}</strong>
            </div>
            <div className="aos-pw-sub">{primary.subtopic}</div>
            <div className="aos-pw-stats">
              <div>
                <span className="aos-pw-num" style={{ color: "var(--danger)" }}>
                  {primary.lost}
                </span>
                <span>marks lost</span>
              </div>
              <div>
                <span className="aos-pw-num">{primary.attempts}</span>
                <span>attempts</span>
              </div>
              <div>
                <span className="aos-pw-num">{primary.avg}%</span>
                <span>avg score</span>
              </div>
            </div>
            <div className="aos-pw-fail">
              <span className="aos-pw-flabel">Primary failure</span> {primary.primary}
            </div>
            <div className="aos-pw-fail">
              <span className="aos-pw-flabel">Secondary</span> {primary.secondary}
            </div>
            <div className="aos-pw-fail">
              <span className="aos-pw-flabel">Examiner trap</span>{" "}
              <Badge tone="amber">Yes · 3 reports</Badge>
            </div>
            <div className="aos-pw-actions">
              <Button variant="primary" icon="target" onClick={() => go("tutor")}>
                Start targeted revision
              </Button>
              <Button variant="ghost" icon="notebook" onClick={() => go("booklets")}>
                Generate booklet
              </Button>
            </div>
          </div>
          <div className="aos-misgraph">
            <div className="aos-mg-title">Misconception graph</div>
            <div className="aos-mg-root">
              {subjectById(primary.subject).name} → {primary.unit} → {primary.topic} →
              Discharging
            </div>
            {primary.breakdown.map((b, i) => (
              <div key={b.tag} className="aos-mg-branch">
                <span className="aos-mg-elbow">
                  {i === primary.breakdown.length - 1 ? "└──" : "├──"}
                </span>
                <span
                  className="aos-mg-tag"
                  style={{
                    background: `color-mix(in oklab, var(--danger) ${Math.round(
                      (b.n / maxOcc) * 60
                    )}%, transparent)`,
                  }}
                >
                  {b.tag}
                </span>
                <span className="aos-mg-count">{b.n} occurrences</span>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* confidence traps */}
      <SectionTitle>Confidence traps · wrong + high confidence</SectionTitle>
      <div className="aos-conftrap-grid">
        {confidenceTraps.map((t, i) => (
          <div key={i} className="aos-conftrap">
            <div className="aos-ct-top">
              <Icon name="alert-octagon" size={16} style={{ color: "var(--danger)" }} />
              <Badge tone="red">
                Conf {t.conf} · {t.score}%
              </Badge>
            </div>
            <div className="aos-ct-text">{t.text}</div>
            <div className="aos-ct-topic">{t.topic}</div>
          </div>
        ))}
      </div>

      {/* weakness table */}
      <div className="aos-head-flex" style={{ marginTop: 26, marginBottom: 12 }}>
        <div style={{ fontSize: 15, fontWeight: 600 }}>All weaknesses</div>
        <div className="aos-filters">
          <div className="aos-seg sm">
            {["all", "physics", "chemistry", "fmaths", "maths", "cs"].map((s) => (
              <button
                key={s}
                className={subj === s ? "active" : ""}
                onClick={() => setSubj(s)}
              >
                {s === "all" ? "All" : subjectById(s).short}
              </button>
            ))}
          </div>
        </div>
      </div>
      <Card pad={false}>
        <table className="aos-table">
          <thead>
            <tr>
              <th>Topic</th>
              <th>Subtopic</th>
              <th
                className="aos-th-sort"
                onClick={() => setSortKey("attempts")}
              >
                Attempts
              </th>
              <th className="aos-th-sort" onClick={() => setSortKey("avg")}>
                Avg score
              </th>
              <th className="aos-th-sort" onClick={() => setSortKey("lost")}>
                Marks lost
              </th>
              <th>Primary mistake</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((w, i) => {
              const [ti, tc] = trendIcon(w.trend);
              return (
                <tr key={i} onClick={() => go("questions")}>
                  <td className="aos-td-strong">
                    {w.topic}
                    {w.trap && (
                      <Icon
                        name="alert-triangle"
                        size={12}
                        style={{ color: "var(--warn)", marginLeft: 5 }}
                      />
                    )}
                  </td>
                  <td className="aos-muted">{w.subtopic}</td>
                  <td>{w.attempts}</td>
                  <td>
                    <span style={{ color: bandColor(masteryBand(w.avg)) }}>{w.avg}%</span>
                  </td>
                  <td>
                    <strong style={{ color: "var(--danger)" }}>{w.lost}</strong>
                  </td>
                  <td>{w.primary}</td>
                  <td>
                    <Icon name={ti} size={16} style={{ color: tc }} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      {/* examiner trap library */}
      <SectionTitle>Examiner trap library</SectionTitle>
      <div className="aos-traplib">
        {examinerTraps.map((t, i) => (
          <Card key={i} className="aos-traplib-card">
            <div className="aos-tl-head">
              <Badge tone="primary">{t.topic}</Badge>
              <span className="aos-tl-freq">{t.freq}× across reports</span>
            </div>
            <div className="aos-tl-text">{t.text}</div>
            <div className="aos-tl-years">
              {t.years.map((y) => (
                <span key={y} className="aos-year">
                  {y}
                </span>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useState } from "react";
import { Card, GradeBadge, Icon, MasteryBar, Metric, SectionTitle } from "@/components/ui";
import { bandColor, gradeFromPct, masteryBand, papers, subjects, subjectById } from "@/lib/data";
import type { Route } from "@/lib/types";

export function Subjects({ go }: { go: (r: Route) => void }) {
  const [active, setActive] = useState("physics");
  const [open, setOpen] = useState<string | null>(null);
  const s = subjectById(active);
  const subjPapers = papers.filter((p) => p.subject === active);

  return (
    <div className="aos-page">
      <div className="aos-tabbar">
        {subjects.map((sub) => (
          <button
            key={sub.id}
            className={`aos-tab ${active === sub.id ? "active" : ""}`}
            onClick={() => { setActive(sub.id); setOpen(null); }}
          >
            {sub.name}
          </button>
        ))}
      </div>

      <div className="aos-subj-head">
        <div>
          <h1>{s.name}</h1>
          <p className="aos-page-sub">{s.board}</p>
        </div>
        <div className="aos-subj-grades">
          <div className="aos-grade-block">
            <span>Current</span>
            <GradeBadge grade={s.current} />
          </div>
          <Icon name="arrow-right" size={16} style={{ color: "var(--text-3)" }} />
          <div className="aos-grade-block">
            <span>Predicted</span>
            <GradeBadge grade={s.predicted} />
          </div>
          <div className="aos-grade-block">
            <span>Confidence</span>
            <strong>{s.confidence}%</strong>
          </div>
        </div>
      </div>

      <div className="aos-metric-row aos-three">
        <Metric label="Papers attempted" value={s.papers} icon="files" />
        <Metric label="Questions attempted" value={s.questions.toLocaleString()} icon="pencil" />
        <Metric label="Average score" value={`${s.avg}%`} icon="percentage" />
      </div>

      <SectionTitle>Units</SectionTitle>
      <div className="aos-unit-grid">
        {s.units.map((u) => {
          const band = masteryBand(u.mastery);
          const isOpen = open === u.code;
          return (
            <div
              key={u.code}
              className={`aos-unit-card ${isOpen ? "open" : ""}`}
              onClick={() => setOpen(isOpen ? null : u.code)}
            >
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
                <span>{u.questions} questions</span>
                <span className="aos-unit-expand">
                  <Icon name={isOpen ? "chevron-up" : "chevron-down"} size={14} /> topics
                </span>
              </div>
              {isOpen && (
                <div
                  className="aos-topic-list"
                  onClick={(e) => e.stopPropagation()}
                >
                  {u.topics.map((t) => (
                    <div key={t.name} className="aos-topic-row">
                      <span className="aos-topic-name">
                        {t.name}
                        {t.trap && (
                          <Icon
                            name="alert-triangle"
                            size={12}
                            style={{ color: "var(--warn)", marginLeft: 5 }}
                          />
                        )}
                      </span>
                      <div>
                        <MasteryBar value={t.mastery} />
                      </div>
                      <span
                        className="aos-topic-pct"
                        style={{ color: bandColor(masteryBand(t.mastery)) }}
                      >
                        {t.mastery}%
                      </span>
                      <span className="aos-topic-q">{t.q}q</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <SectionTitle>Recent attempts</SectionTitle>
      <Card pad={false}>
        <table className="aos-table">
          <thead>
            <tr>
              <th>Paper</th>
              <th>Date</th>
              <th>Score</th>
              <th>Grade</th>
              <th>Time</th>
              <th>vs target</th>
            </tr>
          </thead>
          <tbody>
            {(subjPapers.length ? subjPapers : papers.slice(0, 3)).map((p) => {
              const pct = Math.round((p.score / p.max) * 100);
              const delta = p.time - p.target;
              return (
                <tr key={p.id} onClick={() => go("marking")}>
                  <td className="aos-td-strong">
                    {p.code} · {p.unit}
                  </td>
                  <td>{p.session}</td>
                  <td>
                    {p.score}/{p.max}{" "}
                    <span className="aos-muted">({pct}%)</span>
                  </td>
                  <td>
                    <GradeBadge grade={gradeFromPct(pct)} />
                  </td>
                  <td>{p.time} min</td>
                  <td style={{ color: delta > 0 ? "var(--danger)" : "var(--accent)" }}>
                    {delta > 0 ? "+" : ""}{delta} min
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

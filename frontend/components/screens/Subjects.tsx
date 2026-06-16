"use client";

import { useState } from "react";
import { Card, EmptyState, ErrorState, GradeBadge, Icon, Loading, MasteryBar, Metric, SectionTitle } from "@/components/ui";
import { bandColor, gradeFromPct, masteryBand, SUBJECT_LABELS } from "@/lib/data";
import { getDashboard, getPapers } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Route } from "@/lib/types";
import type { AppSession } from "@/components/ClientLayout";

export function Subjects({ go, session }: { go: (r: Route) => void; session: AppSession }) {
  const [active, setActive] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const dash = useFetch(getDashboard);

  const subjectList = dash.data?.subject_mastery ?? [];
  // Default to the first subject that actually has data instead of a hardcoded
  // "physics" (which shows an empty state when Physics has no data — LOGIC-017).
  const activeId = active ?? subjectList[0]?.subject_id ?? "";
  const papersFetch = useFetch(() => getPapers(activeId), [activeId]);

  if (dash.loading) return <div className="aos-page"><Loading label="Loading subjects…" /></div>;
  if (dash.error || !dash.data) {
    return <div className="aos-page"><ErrorState message={dash.error ?? "No data"} retry={dash.retry} /></div>;
  }

  const s = subjectList.find((x) => x.subject_id === activeId);
  const grades = dash.data.predicted_grades.find((g) => g.subject_id === activeId);
  const attemptedPapers = (papersFetch.data ?? []).filter((p) => p.score != null);
  const labels = SUBJECT_LABELS[activeId];

  return (
    <div className="aos-page">
      <div className="aos-tabbar">
        {subjectList.map((sub) => (
          <button
            key={sub.subject_id}
            className={`aos-tab ${activeId === sub.subject_id ? "active" : ""}`}
            onClick={() => { setActive(sub.subject_id); setOpen(null); }}
          >
            {sub.subject}
          </button>
        ))}
      </div>

      {!s ? (
        <EmptyState title="No syllabus data for this subject" sub="Seed progress.db first." />
      ) : (
        <>
          <div className="aos-subj-head">
            <div>
              <h1>{s.subject}</h1>
              <p className="aos-page-sub">{labels?.board ?? ""}</p>
            </div>
            <div className="aos-subj-grades">
              <div className="aos-grade-block">
                <span>Current</span>
                <GradeBadge grade={s.current_grade} />
              </div>
              <Icon name="arrow-right" size={16} style={{ color: "var(--text-3)" }} />
              <div className="aos-grade-block">
                <span>Predicted</span>
                <GradeBadge grade={s.predicted_grade} />
              </div>
              <div className="aos-grade-block">
                <span>Confidence</span>
                <strong>{grades?.confidence ?? "low"}</strong>
              </div>
            </div>
          </div>

          <div className="aos-metric-row aos-three">
            <Metric label="Papers attempted" value={attemptedPapers.length} icon="files" />
            <Metric label="Topics tracked" value={s.topic_count} icon="list-check" />
            <Metric label="Average mastery" value={`${Math.round(s.mastery_pct)}%`} icon="percentage" />
          </div>

          <SectionTitle>Units</SectionTitle>
          {s.units.length === 0 ? (
            <EmptyState title="No units tracked" />
          ) : (
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
                        <div className="aos-unit-name">{u.topic_count} topics</div>
                      </div>
                      <div className="aos-unit-pct" style={{ color: bandColor(band) }}>
                        {u.mastery}%
                      </div>
                    </div>
                    <MasteryBar value={u.mastery} band={band} height={6} />
                    <div className="aos-unit-foot">
                      <span>{u.questions.toLocaleString()} questions in bank</span>
                      <span className="aos-unit-expand">
                        <Icon name={isOpen ? "chevron-up" : "chevron-down"} size={14} /> topics
                      </span>
                    </div>
                    {isOpen && (
                      <div className="aos-topic-list" onClick={(e) => e.stopPropagation()}>
                        {u.topics.map((t) => (
                          <div key={t.name} className="aos-topic-row">
                            <span className="aos-topic-name">{t.name}</span>
                            <div><MasteryBar value={t.mastery} /></div>
                            <span
                              className="aos-topic-pct"
                              style={{ color: bandColor(masteryBand(t.mastery)) }}
                            >
                              {t.mastery}%
                            </span>
                            <span className="aos-topic-q">
                              {t.reviewed ? "reviewed" : "new"}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          <SectionTitle>Recent attempts</SectionTitle>
          {papersFetch.loading ? (
            <Loading label="Loading attempts…" />
          ) : attemptedPapers.length === 0 ? (
            <Card>
              <span className="aos-muted">
                No attempts on {s.subject} papers yet. Start one from the Timer.
              </span>
            </Card>
          ) : (
            <Card pad={false}>
              <table className="aos-table">
                <thead>
                  <tr>
                    <th>Paper</th><th>Session</th><th>Score</th><th>Grade</th><th>Time</th><th>vs target</th>
                  </tr>
                </thead>
                <tbody>
                  {attemptedPapers.map((p) => {
                    const pct = p.score != null && p.max ? Math.round((p.score / p.max) * 100) : null;
                    const delta = p.time != null && p.target != null ? p.time - p.target : null;
                    return (
                      <tr key={p.id} onClick={() => { session.setPaperId(p.id); go("marking"); }}>
                        <td className="aos-td-strong">{p.code} · {p.unit}</td>
                        <td>{p.session}</td>
                        <td>
                          {p.score}/{p.max}{" "}
                          {pct != null && <span className="aos-muted">({pct}%)</span>}
                        </td>
                        <td>{pct != null && <GradeBadge grade={gradeFromPct(pct)} />}</td>
                        <td>{p.time != null ? `${p.time} min` : "—"}</td>
                        <td style={{ color: delta != null && delta > 0 ? "var(--danger)" : "var(--accent)" }}>
                          {delta != null ? `${delta > 0 ? "+" : ""}${delta} min` : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

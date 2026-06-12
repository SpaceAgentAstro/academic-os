"use client";

import { useState } from "react";
import { Badge, Button, Card, EmptyState, ErrorState, Icon, Loading, SectionTitle } from "@/components/ui";
import { bandColor, masteryBand, subjectName, SUBJECT_LABELS } from "@/lib/data";
import { getDashboard, getWeaknesses } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Route } from "@/lib/types";

export function Weaknesses({ go }: { go: (r: Route) => void }) {
  const [subj, setSubj] = useState("all");
  const [sortKey, setSortKey] = useState<"lost" | "avg" | "attempts">("lost");
  const weak = useFetch(getWeaknesses);
  const dash = useFetch(getDashboard);

  if (weak.loading) return <div className="aos-page"><Loading label="Analysing attempts…" /></div>;
  if (weak.error || !weak.data) {
    return <div className="aos-page"><ErrorState message={weak.error ?? "No data"} retry={weak.retry} /></div>;
  }

  const { weaknesses, confidence_traps, message } = weak.data;
  const traps = dash.data?.examiner_traps ?? [];

  if (weaknesses.length === 0) {
    return (
      <div className="aos-page">
        <div className="aos-page-head">
          <h1>Where your marks are leaking</h1>
          <p className="aos-page-sub">Ranked by marks lost · from your attempt history</p>
        </div>
        <EmptyState
          icon="report-analytics"
          title="No weakness data yet"
          sub={message ?? "Complete and mark some papers — your weaknesses appear here, computed from real attempts."}
        />
        <div style={{ marginTop: 14, textAlign: "center" }}>
          <Button variant="primary" icon="player-play" onClick={() => go("timer")}>
            Start a paper
          </Button>
        </div>

        {traps.length > 0 && (
          <>
            <SectionTitle>Examiner trap library</SectionTitle>
            <div className="aos-traplib">
              {traps.map((t, i) => (
                <Card key={i} className="aos-traplib-card">
                  <div className="aos-tl-head">
                    <Badge tone="primary">{t.topic || t.subject}</Badge>
                    <span className="aos-tl-freq">{t.freq}× across reports</span>
                  </div>
                  <div className="aos-tl-text">{t.text}</div>
                </Card>
              ))}
            </div>
          </>
        )}
      </div>
    );
  }

  const primary = weaknesses[0];
  const maxOcc = Math.max(1, ...primary.breakdown.map((b) => b.n));

  let rows = weaknesses.filter((w) => subj === "all" || w.subject === subj);
  rows = [...rows].sort((a, b) =>
    sortKey === "lost" ? b.lost - a.lost : sortKey === "avg" ? a.avg - b.avg : b.attempts - a.attempts
  );

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
              {subjectName(primary.subject)} → {primary.unit} → <strong>{primary.topic}</strong>
            </div>
            {primary.subtopic && <div className="aos-pw-sub">{primary.subtopic}</div>}
            <div className="aos-pw-stats">
              <div>
                <span className="aos-pw-num" style={{ color: "var(--danger)" }}>{primary.lost}</span>
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
            {primary.primary && (
              <div className="aos-pw-fail">
                <span className="aos-pw-flabel">Primary failure</span> {primary.primary}
              </div>
            )}
            {primary.secondary && (
              <div className="aos-pw-fail">
                <span className="aos-pw-flabel">Secondary</span> {primary.secondary}
              </div>
            )}
            <div className="aos-pw-actions">
              <Button variant="primary" icon="player-play" onClick={() => go("timer")}>
                Practise this topic
              </Button>
            </div>
          </div>
          {primary.breakdown.length > 0 && (
            <div className="aos-misgraph">
              <div className="aos-mg-title">Mistake breakdown</div>
              <div className="aos-mg-root">
                {subjectName(primary.subject)} → {primary.unit} → {primary.topic}
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
                  <span className="aos-mg-count">{b.n} occurrence{b.n === 1 ? "" : "s"}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      {/* confidence traps */}
      {confidence_traps.length > 0 && (
        <>
          <SectionTitle>Confidence traps · wrong + high confidence</SectionTitle>
          <div className="aos-conftrap-grid">
            {confidence_traps.map((t, i) => (
              <div key={i} className="aos-conftrap">
                <div className="aos-ct-top">
                  <Icon name="alert-octagon" size={16} style={{ color: "var(--danger)" }} />
                  <Badge tone="red">Conf {t.conf} · {t.score}%</Badge>
                </div>
                <div className="aos-ct-text">{t.text}</div>
                <div className="aos-ct-topic">{t.topic}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* weakness table */}
      <div className="aos-head-flex" style={{ marginTop: 26, marginBottom: 12 }}>
        <div style={{ fontSize: 15, fontWeight: 600 }}>All weaknesses</div>
        <div className="aos-filters">
          <div className="aos-seg sm">
            {["all", "physics", "chemistry", "fmaths", "maths", "cs"].map((s) => (
              <button key={s} className={subj === s ? "active" : ""} onClick={() => setSubj(s)}>
                {s === "all" ? "All" : SUBJECT_LABELS[s]?.short ?? s}
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
              <th className="aos-th-sort" onClick={() => setSortKey("attempts")}>Attempts</th>
              <th className="aos-th-sort" onClick={() => setSortKey("avg")}>Avg score</th>
              <th className="aos-th-sort" onClick={() => setSortKey("lost")}>Marks lost</th>
              <th>Primary mistake</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((w, i) => (
              <tr key={i}>
                <td className="aos-td-strong">{w.topic}</td>
                <td className="aos-muted">{w.subtopic}</td>
                <td>{w.attempts}</td>
                <td>
                  <span style={{ color: bandColor(masteryBand(w.avg)) }}>{w.avg}%</span>
                </td>
                <td><strong style={{ color: "var(--danger)" }}>{w.lost}</strong></td>
                <td>{w.primary || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* examiner trap library */}
      {traps.length > 0 && (
        <>
          <SectionTitle>Examiner trap library</SectionTitle>
          <div className="aos-traplib">
            {traps.map((t, i) => (
              <Card key={i} className="aos-traplib-card">
                <div className="aos-tl-head">
                  <Badge tone="primary">{t.topic || t.subject}</Badge>
                  <span className="aos-tl-freq">{t.freq}× across reports</span>
                </div>
                <div className="aos-tl-text">{t.text}</div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

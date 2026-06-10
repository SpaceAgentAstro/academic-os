"use client";

import { useState } from "react";
import { Badge, Button, Card, Icon, SectionTitle } from "@/components/ui";
import { bandColor, masteryBand, subjectById } from "@/lib/data";
import { useWeaknesses, useDashboard } from "@/lib/hooks";
import type { Route, SessionParams } from "@/lib/types";

function Skeleton({ h }: { h?: number }) {
  return <div className="aos-skeleton" style={{ height: h ?? 18, borderRadius: 4 }} />;
}

export function Weaknesses({ go }: { go: (r: Route, p?: SessionParams) => void }) {
  const [subj, setSubj] = useState("all");
  const [sortKey, setSortKey] = useState<"lost" | "avg" | "attempts">("lost");
  const { data: weaknesses, loading } = useWeaknesses();
  const { data: dash } = useDashboard();
  const traps = dash.examiner_traps;

  let rows = weaknesses.filter((w) => subj === "all" || w.subject === subj);
  rows = [...rows].sort((a, b) =>
    sortKey === "lost" ? b.lost - a.lost : sortKey === "avg" ? a.avg - b.avg : b.attempts - a.attempts
  );

  const primary = weaknesses[0];

  return (
    <div className="aos-page">
      <div className="aos-page-head">
        <h1>Where your marks are leaking</h1>
        <p className="aos-page-sub">
          Ranked by marks lost · pulled from your attempt history and examiner reports
        </p>
      </div>

      {loading ? (
        <Card><Skeleton h={160} /></Card>
      ) : !primary ? (
        <Card>
          <div className="aos-empty-state" style={{ padding: 24 }}>
            <Icon name="circle-check" size={22} style={{ color: "var(--accent)" }} />
            <span>
              No weaknesses recorded yet. Complete and mark a paper — modules where you lose
              marks will surface here automatically.
            </span>
          </div>
        </Card>
      ) : (
        <Card className="aos-primary-weak">
          <div className="aos-pw-flag">
            <Icon name="alert-triangle" size={15} /> Most critical weakness
          </div>
          <div>
            <div className="aos-pw-path">
              {subjectById(primary.subject)?.name ?? primary.subject} →{" "}
              <strong>{primary.unit}</strong>
            </div>
            <div className="aos-pw-stats">
              <div>
                <span className="aos-pw-num" style={{ color: "var(--danger)" }}>
                  {primary.lost}
                </span>
                <span>marks lost</span>
              </div>
              <div>
                <span className="aos-pw-num">{primary.attempts}</span>
                <span>questions marked</span>
              </div>
              <div>
                <span className="aos-pw-num">{primary.avg}%</span>
                <span>avg score</span>
              </div>
            </div>
            <div className="aos-pw-fail">
              <span className="aos-pw-flabel">Top examiner note</span> {primary.primary}
            </div>
            {primary.secondary && (
              <div className="aos-pw-fail">
                <span className="aos-pw-flabel">Also</span> {primary.secondary}
              </div>
            )}
            <div className="aos-pw-actions">
              <Button variant="primary" icon="player-play" onClick={() => go("analytics")}>
                Practise this module
              </Button>
            </div>
          </div>
        </Card>
      )}

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
                {s === "all" ? "All" : subjectById(s)?.short ?? s}
              </button>
            ))}
          </div>
        </div>
      </div>
      <Card pad={false}>
        {rows.length === 0 ? (
          <div className="aos-empty-state" style={{ padding: 24 }}>
            <Icon name="file-x" size={18} style={{ color: "var(--text-3)" }} />
            <span>No marked questions for this filter yet.</span>
          </div>
        ) : (
          <table className="aos-table">
            <thead>
              <tr>
                <th>Module</th>
                <th className="aos-th-sort" onClick={() => setSortKey("attempts")}>Questions</th>
                <th className="aos-th-sort" onClick={() => setSortKey("avg")}>Avg score</th>
                <th className="aos-th-sort" onClick={() => setSortKey("lost")}>Marks lost</th>
                <th>Top examiner note</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((w, i) => (
                <tr key={i}>
                  <td className="aos-td-strong">
                    {w.unit}
                    {w.trap && (
                      <Icon
                        name="alert-triangle"
                        size={12}
                        style={{ color: "var(--warn)", marginLeft: 5 }}
                      />
                    )}
                  </td>
                  <td>{w.attempts}</td>
                  <td>
                    <span style={{ color: bandColor(masteryBand(w.avg)) }}>{w.avg}%</span>
                  </td>
                  <td>
                    <strong style={{ color: "var(--danger)" }}>{w.lost}</strong>
                  </td>
                  <td className="aos-muted" style={{ maxWidth: 360 }}>{w.primary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* examiner trap library — real misconceptions */}
      <SectionTitle>Examiner trap library</SectionTitle>
      {traps.length === 0 ? (
        <Card>
          <div className="aos-empty-state" style={{ padding: 24 }}>
            <Icon name="file-description" size={18} style={{ color: "var(--text-3)" }} />
            <span>Examiner reports not yet extracted. Run the extraction pipeline to unlock this.</span>
          </div>
        </Card>
      ) : (
        <div className="aos-traplib">
          {traps.map((t, i) => (
            <Card key={i} className="aos-traplib-card">
              <div className="aos-tl-head">
                <Badge tone="primary">{t.topic || "General"}</Badge>
                <span className="aos-tl-freq">{t.freq}× across reports</span>
              </div>
              <div className="aos-tl-text">{t.text}</div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

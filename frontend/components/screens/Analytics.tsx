"use client";

import { useState } from "react";
import { Badge, Button, Card, Icon, Metric, SectionTitle } from "@/components/ui";
import { BarChart, LineChart, ScatterChart } from "@/components/charts";
import { bandColor, calibration, masteryBand, papers, scoreTrend, subjects, subjectById } from "@/lib/data";
import { useCoverage, useRawPapers } from "@/lib/hooks";
import type { Route, SessionParams } from "@/lib/types";

const topicsLost = [
  { t: "Capacitance", m: 47 }, { t: "Organic synthesis", m: 39 }, { t: "Series (FP2)", m: 31 },
  { t: "Electric fields", m: 28 }, { t: "Logarithms", m: 26 }, { t: "Acid–base", m: 22 },
  { t: "Recursion", m: 18 }, { t: "Resistivity", m: 16 }, { t: "Equilibria", m: 14 }, { t: "Vectors", m: 9 },
];

export function Analytics({ go }: { go: (r: Route, p?: SessionParams) => void }) {
  const [range, setRange] = useState("30 days");
  const coverage = useCoverage();
  const { data: rawPapers, loading: papersLoading } = useRawPapers();

  // Total questions available across all subjects from the live DB
  const totalQAvailable = coverage.reduce((s, c) => s + c.total_questions, 0);
  const totalPapersAvailable = coverage.reduce((s, c) => s + c.papers, 0);

  const scatter = papers.map((p) => ({
    x: p.time,
    y: Math.round((p.score / p.max) * 100),
    label: p.code,
  }));

  return (
    <div className="aos-page">
      <div className="aos-page-head aos-head-flex">
        <div>
          <h1>Analytics</h1>
          <p className="aos-page-sub">Performance intelligence across all subjects</p>
        </div>
        <div className="aos-seg">
          {["7 days", "30 days", "All time"].map((r) => (
            <button key={r} className={range === r ? "active" : ""} onClick={() => setRange(r)}>
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="aos-metric-row">
        <Metric
          label="Question bank"
          value={totalQAvailable > 0 ? totalQAvailable.toLocaleString() : "847"}
          sub={totalPapersAvailable > 0 ? `${totalPapersAvailable} papers ingested` : "of 2,260 attempted"}
          icon="database"
        />
        <Metric
          label="Average score"
          value="71.4%"
          sub="+3.2 pts this month"
          accent="var(--accent)"
          icon="percentage"
        />
        <Metric label="Avg time / question" value="4m 12s" sub="Target 3m 30s" icon="clock" />
        <Metric label="Efficiency" value="17.2" sub="marks per hour" icon="bolt" />
      </div>

      <div className="aos-chart-grid">
        <Card>
          <SectionTitle>Score trend · last 20 papers</SectionTitle>
          <LineChart
            labels={scoreTrend.map((_, i) => i + 1)}
            datasets={[{ data: scoreTrend }]}
            yMin={50}
            yMax={100}
            fmt={(v) => `${v}%`}
            height={210}
          />
        </Card>
        <Card>
          <SectionTitle>Marks lost by topic · top 10</SectionTitle>
          <BarChart
            labels={topicsLost.map((x) => x.t)}
            data={topicsLost.map((x) => x.m)}
            colors={topicsLost.map((x) =>
              x.m > 35
                ? "var(--danger)"
                : x.m > 22
                ? "var(--warn)"
                : "var(--primary)"
            )}
            horizontal
            max={50}
            height={260}
          />
        </Card>
        <Card>
          <SectionTitle>Time vs score · each dot is a paper</SectionTitle>
          <ScatterChart points={scatter} height={240} />
        </Card>
        <Card>
          <SectionTitle>Mastery distribution by subject</SectionTitle>
          <BarChart
            labels={subjects.map((s) => s.short)}
            stacked
            height={240}
            datasets={[
              {
                label: ">80%",
                data: subjects.map((s) => s.units.filter((u) => u.mastery >= 80).length),
                backgroundColor: "var(--accent)",
                borderRadius: 3,
              },
              {
                label: "50–80%",
                data: subjects.map(
                  (s) => s.units.filter((u) => u.mastery >= 50 && u.mastery < 80).length
                ),
                backgroundColor: "var(--warn)",
                borderRadius: 3,
              },
              {
                label: "<50%",
                data: subjects.map((s) => s.units.filter((u) => u.mastery < 50).length),
                backgroundColor: "var(--danger)",
                borderRadius: 3,
              },
            ]}
          />
        </Card>
      </div>

      <Card>
        <SectionTitle>Confidence calibration</SectionTitle>
        <div className="aos-calib">
          <div>
            <BarChart
              labels={calibration.map((c) => `Conf ${c.conf}`)}
              data={calibration.map((c) => c.score)}
              colors={calibration.map((c) => bandColor(masteryBand(c.score)))}
              max={100}
              fmt={(v) => `${v}%`}
              height={180}
            />
          </div>
          <div className="aos-calib-notes">
            <div className="aos-calib-note danger">
              <Icon name="trending-down" size={16} />
              <span>
                You are <strong>overconfident</strong> in Logarithms — confidence 4 avg, actual
                score 41%.
              </span>
            </div>
            <div className="aos-calib-note accent">
              <Icon name="trending-up" size={16} />
              <span>
                You are <strong>underconfident</strong> in Mechanics — confidence 2 avg, actual
                score 78%.
              </span>
            </div>
          </div>
        </div>
      </Card>

      <SectionTitle>Session log</SectionTitle>
      <Card pad={false}>
        <table className="aos-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Paper</th>
              <th>Subject</th>
              <th>Unit</th>
              <th>Score</th>
              <th>Grade</th>
              <th>Time</th>
              <th>Target</th>
              <th>Δ</th>
            </tr>
          </thead>
          <tbody>
            {papers.map((p) => {
              const pct = Math.round((p.score / p.max) * 100);
              const delta = p.time - p.target;
              return (
                <tr key={p.id} onClick={() => go("marking")}>
                  <td>{p.session}</td>
                  <td className="aos-td-strong">{p.code}</td>
                  <td>{subjectById(p.subject).name}</td>
                  <td>{p.unit}</td>
                  <td>
                    {p.score}/{p.max}
                  </td>
                  <td>{pct}%</td>
                  <td>{p.time}m</td>
                  <td>{p.target}m</td>
                  <td style={{ color: delta > 0 ? "var(--danger)" : "var(--accent)" }}>
                    {delta > 0 ? "+" : ""}
                    {delta}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>

      <>
        <SectionTitle
          action={
            rawPapers.length > 0 ? (
              <span className="aos-muted" style={{ fontSize: 12 }}>
                {rawPapers.length} papers · question_bank.db
              </span>
            ) : undefined
          }
        >
          Paper library
        </SectionTitle>
        <Card pad={false}>
          {papersLoading ? (
            <div style={{ padding: 24, color: "var(--text-3)" }}>Loading papers…</div>
          ) : rawPapers.length === 0 ? (
            <div className="aos-empty-state" style={{ padding: 32 }}>
              <Icon name="database" size={20} style={{ color: "var(--text-3)" }} />
              <span>No papers found in question_bank.db. Run the ingestion pipeline to populate.</span>
            </div>
          ) : (
            <table className="aos-table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Subject</th>
                  <th>Unit</th>
                  <th>Session</th>
                  <th>Questions</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rawPapers.slice(0, 50).map((p) => (
                  <tr key={p.id}>
                    <td className="aos-td-strong">{p.code}</td>
                    <td>{subjectById(p.subject)?.name ?? p.subject}</td>
                    <td>{p.unit}</td>
                    <td>{p.session}</td>
                    <td>{p.question_count}</td>
                    <td>
                      {p.score != null ? (
                        <Badge tone="green">{Math.round((p.score / (p.max ?? 1)) * 100)}%</Badge>
                      ) : (
                        <span className="aos-muted" style={{ fontSize: 12 }}>Not attempted</span>
                      )}
                    </td>
                    <td>
                      <Button
                        variant="primary"
                        size="sm"
                        icon="player-play"
                        onClick={() =>
                          go("timer", {
                            paperId: String(p.id),
                            paperCode: p.code,
                            paperUnit: p.unit,
                            paperSession: p.session,
                          })
                        }
                      >
                        Start
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </>
    </div>
  );
}

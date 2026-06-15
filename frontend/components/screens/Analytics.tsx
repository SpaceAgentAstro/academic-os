"use client";

import { Card, EmptyState, ErrorState, Loading, Metric, SectionTitle } from "@/components/ui";
import { BarChart, LineChart, ScatterChart } from "@/components/charts";
import { bandColor, gradeFromPct, masteryBand, subjectName } from "@/lib/data";
import { getAnalytics, getCoverage, getPapers, getWeaknesses } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Route } from "@/lib/types";
import type { AppSession } from "@/components/ClientLayout";

export function Analytics({ go, session }: { go: (r: Route) => void; session: AppSession }) {
  const openPaper = (paperId: string) => {
    session.setPaperId(paperId);
    session.setSessionId(null);
    go("marking");
  };
  const analytics = useFetch(getAnalytics);
  const coverage = useFetch(getCoverage);
  const papersFetch = useFetch(() => getPapers());
  const weak = useFetch(getWeaknesses);

  if (analytics.loading || coverage.loading) {
    return <div className="aos-page"><Loading label="Loading analytics…" /></div>;
  }
  if (analytics.error || coverage.error) {
    return (
      <div className="aos-page">
        <ErrorState
          message={analytics.error ?? coverage.error ?? "No data"}
          retry={analytics.error ? analytics.retry : coverage.retry}
        />
      </div>
    );
  }

  const cov = coverage.data ?? [];
  const a = analytics.data;
  const papers = papersFetch.data ?? [];
  const attempted = papers.filter((p) => p.score != null && p.max);
  const weaknesses = weak.data?.weaknesses ?? [];
  const calibration = a?.calibration ?? [];

  const totalQAvailable = cov.reduce((s, c) => s + c.total_questions, 0);
  const totalPapersAvailable = cov.reduce((s, c) => s + c.papers, 0);
  const totalAttempted = cov.reduce((s, c) => s + c.attempted, 0);

  const avgScore = a && a.score_trend.length
    ? Math.round(a.score_trend.reduce((x, y) => x + y, 0) / a.score_trend.length)
    : null;

  const scatter = attempted
    .filter((p) => p.time != null)
    .map((p) => ({
      x: p.time as number,
      y: Math.round(((p.score as number) / (p.max as number)) * 100),
      label: p.code,
    }));

  const topicsLost = weaknesses.slice(0, 10);

  return (
    <div className="aos-page">
      <div className="aos-page-head">
        <h1>Analytics</h1>
        <p className="aos-page-sub">Performance intelligence · every number from a real query</p>
      </div>

      <div className="aos-metric-row">
        <Metric
          label="Question bank"
          value={totalQAvailable.toLocaleString()}
          sub={`${totalPapersAvailable.toLocaleString()} papers ingested`}
          icon="database"
        />
        <Metric
          label="Questions attempted"
          value={totalAttempted.toLocaleString()}
          sub={totalQAvailable ? `${Math.round((totalAttempted / totalQAvailable) * 1000) / 10}% of bank` : ""}
          icon="pencil"
        />
        <Metric
          label="Average score"
          value={avgScore != null ? `${avgScore}%` : "—"}
          sub={a ? `${a.sessions} completed sessions` : "No sessions yet"}
          accent={avgScore != null ? "var(--accent)" : undefined}
          icon="percentage"
        />
        <Metric
          label="Marked papers"
          value={attempted.length}
          sub={attempted.length === 0 ? "Start your first paper" : "with real scores"}
          icon="files"
        />
      </div>

      <div className="aos-chart-grid">
        <Card>
          <SectionTitle>Score trend · completed sessions</SectionTitle>
          {a && a.score_trend.length >= 2 ? (
            <LineChart
              labels={a.score_trend.map((_, i) => i + 1)}
              datasets={[{ data: a.score_trend }]}
              yMin={0}
              yMax={100}
              fmt={(v) => `${v}%`}
              height={210}
            />
          ) : (
            <EmptyState
              icon="chart-line"
              title="Not enough sessions"
              sub="Complete at least two marked papers to see your trend."
            />
          )}
        </Card>
        <Card>
          <SectionTitle>Marks lost by topic · top 10</SectionTitle>
          {topicsLost.length > 0 ? (
            <BarChart
              labels={topicsLost.map((x) => x.topic)}
              data={topicsLost.map((x) => x.lost)}
              colors={topicsLost.map((x) =>
                x.lost > 35 ? "var(--danger)" : x.lost > 22 ? "var(--warn)" : "var(--primary)"
              )}
              horizontal
              max={Math.max(10, ...topicsLost.map((x) => x.lost))}
              height={260}
            />
          ) : (
            <EmptyState
              icon="chart-bar"
              title="No marked attempts yet"
              sub="Mark some papers to see where marks are lost."
            />
          )}
        </Card>
        <Card>
          <SectionTitle>Time vs score · each dot is a paper</SectionTitle>
          {scatter.length > 0 ? (
            <ScatterChart points={scatter} height={240} />
          ) : (
            <EmptyState icon="chart-dots" title="No timed papers yet" />
          )}
        </Card>
        <Card>
          <SectionTitle>Confidence calibration</SectionTitle>
          {calibration.length > 0 ? (
            <BarChart
              labels={calibration.map((c) => `Conf ${c.conf}`)}
              data={calibration.map((c) => c.score)}
              colors={calibration.map((c) => bandColor(masteryBand(c.score)))}
              max={100}
              fmt={(v) => `${v}%`}
              height={180}
            />
          ) : (
            <EmptyState
              icon="adjustments"
              title="No confidence data"
              sub="Rate confidence while marking to see calibration."
            />
          )}
        </Card>
      </div>

      <SectionTitle>Session log</SectionTitle>
      {attempted.length === 0 ? (
        <Card>
          <span className="aos-muted">No attempts yet. Start your first paper from the Timer.</span>
        </Card>
      ) : (
        <Card pad={false}>
          <table className="aos-table">
            <thead>
              <tr>
                <th>Paper</th><th>Subject</th><th>Unit</th><th>Session</th>
                <th>Score</th><th>Grade</th><th>Time</th><th>Target</th><th>Δ</th>
              </tr>
            </thead>
            <tbody>
              {attempted.map((p) => {
                const pct = Math.round(((p.score as number) / (p.max as number)) * 100);
                const delta = p.time != null && p.target != null ? p.time - p.target : null;
                return (
                  <tr key={p.id} onClick={() => openPaper(p.id)}>
                    <td className="aos-td-strong">{p.code}</td>
                    <td>{subjectName(p.subject)}</td>
                    <td>{p.unit}</td>
                    <td>{p.session}</td>
                    <td>{p.score}/{p.max}</td>
                    <td>{gradeFromPct(pct)}</td>
                    <td>{p.time != null ? `${p.time}m` : "—"}</td>
                    <td>{p.target != null ? `${p.target}m` : "—"}</td>
                    <td style={{ color: delta != null && delta > 0 ? "var(--danger)" : "var(--accent)" }}>
                      {delta != null ? `${delta > 0 ? "+" : ""}${delta}` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      )}

      <SectionTitle
        action={
          <span className="aos-muted" style={{ fontSize: 12 }}>
            {papers.length.toLocaleString()} papers · question_bank.db
          </span>
        }
      >
        Paper library
      </SectionTitle>
      {papersFetch.loading ? (
        <Loading label="Loading paper library…" />
      ) : papers.length === 0 ? (
        <EmptyState title="No papers ingested" sub="Drop PDFs into papers/ and run the ingestion pipeline." />
      ) : (
        <Card pad={false}>
          <table className="aos-table">
            <thead>
              <tr>
                <th>Code</th><th>Subject</th><th>Unit</th><th>Session</th><th>Questions</th><th>Status</th>
              </tr>
            </thead>
            <tbody>
              {papers.slice(0, 50).map((p) => (
                <tr key={p.id}>
                  <td className="aos-td-strong">{p.full_code}</td>
                  <td>{subjectName(p.subject)}</td>
                  <td>{p.unit}</td>
                  <td>{p.session}</td>
                  <td>{p.question_count}</td>
                  <td>
                    {p.score != null ? (
                      <span style={{ color: "var(--accent)", fontSize: 12 }}>
                        {p.score}/{p.max}
                      </span>
                    ) : (
                      <span className="aos-muted" style={{ fontSize: 12 }}>Not attempted</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

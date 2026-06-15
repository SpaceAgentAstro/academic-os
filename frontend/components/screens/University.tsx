"use client";

import { Card, EmptyState, ErrorState, GradeBadge, Loading, SectionTitle } from "@/components/ui";
import { getDashboard } from "@/lib/api";
import { useFetch } from "@/lib/hooks";

export function University() {
  const { data, loading, error, retry } = useFetch(getDashboard);

  if (loading) return <div className="aos-page aos-narrow"><Loading label="Loading grades…" /></div>;
  if (error || !data) {
    return <div className="aos-page aos-narrow"><ErrorState message={error ?? "No data"} retry={retry} /></div>;
  }

  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head">
        <h1>University readiness</h1>
        <p className="aos-page-sub">Predicted grades vs entry requirements</p>
      </div>

      <EmptyState
        icon="school"
        title="No target universities configured"
        sub="University tracking needs your target courses and entry requirements. There is no universities table in the databases yet — once targets are added, readiness is computed from your real predicted grades below."
      />

      <SectionTitle>Current predicted grades (from real mastery data)</SectionTitle>
      {data.predicted_grades.length === 0 ? (
        <EmptyState title="No mastery data" sub="Seed progress.db and complete papers first." />
      ) : (
        <Card pad={false}>
          <table className="aos-table">
            <thead>
              <tr>
                <th>Subject</th><th>Current</th><th>Predicted</th><th>Confidence</th><th>Attempts</th>
              </tr>
            </thead>
            <tbody>
              {data.predicted_grades.map((g) => (
                <tr key={g.subject_id}>
                  <td className="aos-td-strong">{g.subject}</td>
                  <td><GradeBadge grade={g.current} /></td>
                  <td><GradeBadge grade={g.predicted} /></td>
                  <td>{g.confidence}</td>
                  <td>{g.attempt_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

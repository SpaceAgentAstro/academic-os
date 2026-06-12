"use client";

import { Badge, Card, GradeBadge, Icon, SectionTitle } from "@/components/ui";
import { LineChart } from "@/components/charts";
import { readinessTimeline, requirements, universities } from "@/lib/data";

export function University() {
  return (
    <div className="aos-page">
      <div className="aos-page-head">
        <h1>University readiness</h1>
        <p className="aos-page-sub">
          Tracking your offer requirements against predicted performance
        </p>
      </div>

      <div className="aos-uni-grid">
        {universities.map((u) => (
          <Card key={u.name} className="aos-uni-card">
            <div className="aos-uni-head">
              <div>
                <div className="aos-uni-name">{u.name}</div>
                <div className="aos-uni-course">{u.course}</div>
              </div>
              <Badge tone={u.confidence === "High" ? "green" : u.confidence === "Medium" ? "amber" : "red"}>
                {u.confidence}
              </Badge>
            </div>
            <div className="aos-uni-req">
              <div className="aos-uni-reqcol">
                <span>Requires</span>
                <div className="aos-grade-row">
                  {u.reqGrades.map((g, i) => (
                    <GradeBadge key={i} grade={g} />
                  ))}
                </div>
              </div>
              <Icon name="arrow-right" size={14} style={{ color: "var(--text-3)" }} />
              <div className="aos-uni-reqcol">
                <span>Your current</span>
                <div className="aos-grade-row">
                  {u.current.map((g, i) => (
                    <GradeBadge key={i} grade={g} />
                  ))}
                </div>
              </div>
            </div>
            <div className="aos-uni-readwrap">
              <div className="aos-uni-readtop">
                <div className="aos-uni-readnum">
                  {u.readiness}%<span>ready now</span>
                </div>
                <div className="aos-uni-readpred">
                  Predicted <strong>{u.predicted}%</strong>
                </div>
              </div>
              <div className="aos-mbar" style={{ height: 6 }}>
                <div
                  className="aos-mbar-fill"
                  style={{ width: `${u.readiness}%`, background: "var(--primary)" }}
                />
              </div>
              <div className="aos-uni-readmeta">
                <span className="aos-muted">Trend to exam</span>
                <span className="aos-uni-trend">
                  <Icon
                    name={u.trend === "up" ? "trending-up" : u.trend === "down" ? "trending-down" : "minus"}
                    size={14}
                  />{" "}
                  {u.trend === "up" ? "Improving" : u.trend === "down" ? "Declining" : "Stable"}
                </span>
              </div>
            </div>
            <div className="aos-uni-risks">
              <span className="aos-risk-label">Risk factors</span>
              {u.risks.map((r, i) => (
                <div key={i} className="aos-risk">
                  <Icon name="point" size={14} style={{ color: "var(--warn)" }} />
                  {r}
                </div>
              ))}
            </div>
          </Card>
        ))}
      </div>

      <Card>
        <SectionTitle>Overall readiness timeline · projected to June exam</SectionTitle>
        <LineChart
          labels={readinessTimeline.labels}
          datasets={[{ data: readinessTimeline.values, pointRadius: 3 }]}
          yMin={50}
          yMax={100}
          fmt={(v) => `${v}%`}
          height={220}
        />
      </Card>

      <SectionTitle>Subject requirements checker</SectionTitle>
      <Card pad={false}>
        <table className="aos-table">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Required</th>
              <th>Current</th>
              <th>Predicted</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {requirements.map((r) => (
              <tr key={r.subject}>
                <td className="aos-td-strong">{r.subject}</td>
                <td>
                  <GradeBadge grade={r.required} />
                </td>
                <td>
                  <GradeBadge grade={r.current} />
                </td>
                <td>
                  <GradeBadge grade={r.predicted} />
                </td>
                <td>
                  <Badge
                    tone={
                      r.status === "exceed"
                        ? "green"
                        : r.status === "track"
                        ? "primary"
                        : "red"
                    }
                  >
                    {r.status === "exceed"
                      ? "Exceeding"
                      : r.status === "track"
                      ? "On track"
                      : "At risk"}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

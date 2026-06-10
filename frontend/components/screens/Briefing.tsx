"use client";

import { Badge, Button, Card, Icon, MasteryBar, SectionTitle } from "@/components/ui";
import { coverage, dueReviews, questionOfDay, todayStr } from "@/lib/data";
import type { Route } from "@/lib/types";

export function Briefing({ go }: { go: (r: Route) => void }) {
  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head">
        <h1>Today&apos;s briefing</h1>
        <p className="aos-page-sub">{todayStr()} · spaced repetition + examiner intelligence</p>
      </div>

      <Card pad={false}>
        <SectionTitle>
          <Icon name="refresh" size={15} style={{ marginRight: 6, color: "var(--primary)" }} />
          Revision focus
        </SectionTitle>
        <div className="aos-list">
          {dueReviews.map((r, i) => (
            <div key={i} className="aos-due-row">
              <div className="aos-due-num">{i + 1}</div>
              <div className="aos-due-name">{r.topic}</div>
              <Badge tone={r.overdue ? "red" : "amber"}>{r.status}</Badge>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <SectionTitle>
          <Icon name="help-circle" size={15} style={{ marginRight: 6, color: "var(--primary)" }} />
          Question of the day
        </SectionTitle>
        <div className="aos-qod-meta" style={{ marginTop: 4 }}>
          {questionOfDay.topic} · {questionOfDay.unit} · {questionOfDay.marks} marks ·{" "}
          <Badge tone="red">{questionOfDay.difficulty}</Badge>
        </div>
        <p className="aos-briefing-q">{questionOfDay.text}</p>
        <Button variant="primary" icon="player-play" onClick={() => go("timer")}>
          Attempt now
        </Button>
      </Card>

      <Card pad={false}>
        <SectionTitle>
          <Icon name="binoculars" size={15} style={{ marginRight: 6, color: "var(--primary)" }} />
          Examiner intelligence
        </SectionTitle>
        <div style={{ padding: "0 20px 18px" }}>
          <div className="aos-focus-tag">
            Today&apos;s focus topic: <strong>Capacitance</strong>
          </div>
          <div className="aos-trap-list" style={{ marginTop: 10 }}>
            <div className="aos-trap">
              <Icon name="quote" size={15} style={{ color: "var(--warn)", flexShrink: 0, marginTop: 2 }} />
              <div>
                <div className="aos-trap-text">
                  &ldquo;June 2023: Most candidates who attempted Q8 failed to apply natural logarithms
                  correctly.&rdquo;
                </div>
              </div>
            </div>
            <div className="aos-trap">
              <Icon name="quote" size={15} style={{ color: "var(--warn)", flexShrink: 0, marginTop: 2 }} />
              <div>
                <div className="aos-trap-text">
                  &ldquo;Jan 2022: Common error — forgetting the negative sign in exponential decay.&rdquo;
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card pad={false}>
        <SectionTitle action={<Badge tone="green">9 day streak</Badge>}>
          Coverage summary
        </SectionTitle>
        <div style={{ padding: "0 20px 18px" }}>
          {coverage.map((c) => (
            <div key={c.subject} className="aos-cov-row">
              <span className="aos-cov-name">{c.subject}</span>
              <MasteryBar
                value={c.pct}
                band={c.pct >= 60 ? "green" : c.pct >= 40 ? "amber" : "red"}
              />
              <span className="aos-cov-meta">
                {c.attempted} attempted · {c.pct}%
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

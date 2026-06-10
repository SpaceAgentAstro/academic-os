"use client";

import { type ReactNode } from "react";
import { Badge, Button, Card, Icon, SectionTitle } from "@/components/ui";
import { booklet, todayStr } from "@/lib/data";

function Section({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <Card className="aos-bk-section">
      <div className="aos-bk-num">{n}</div>
      <div className="aos-bk-body">
        <SectionTitle>{title}</SectionTitle>
        {children}
      </div>
    </Card>
  );
}

export function Booklet() {
  const b = booklet;
  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head aos-head-flex">
        <div>
          <h1>{b.topic}</h1>
          <p className="aos-page-sub">
            {b.subject} · {b.unit} · generated {todayStr()}
          </p>
        </div>
        <div className="aos-bk-actions">
          <Button variant="primary" icon="download">
            Download PDF
          </Button>
          <Button variant="ghost" icon="send">
            Send to Telegram
          </Button>
        </div>
      </div>

      <Section n={1} title="Theory summary">
        {b.theory.map((p, i) => (
          <p key={i} className="aos-bk-p">
            {p}
          </p>
        ))}
      </Section>

      <Section n={2} title="Key definitions">
        <div className="aos-bk-defs">
          {b.definitions.map((d, i) => (
            <div key={i} className="aos-bk-def">
              <span className="aos-bk-term">{d.term}</span>
              <span className="aos-bk-defv">{d.def}</span>
              <Badge tone="primary">{d.marks} mark</Badge>
            </div>
          ))}
        </div>
      </Section>

      <Section n={3} title="Formula sheet">
        <div className="aos-bk-formulae">
          {b.formulae.map((f, i) => (
            <div key={i} className="aos-bk-formula">
              <span className="aos-bk-eq">{f.eq}</span>
              <span className="aos-bk-vars">{f.vars}</span>
            </div>
          ))}
        </div>
      </Section>

      <Section n={4} title="Worked example">
        <p className="aos-bk-p">
          <strong>Q.</strong> {b.worked.q}
        </p>
        <div className="aos-bk-steps">
          {b.worked.steps.map((s, i) => (
            <div key={i} className="aos-bk-step">
              <span className="aos-bk-stepn">{i + 1}</span>
              {s}
            </div>
          ))}
        </div>
      </Section>

      <Section n={5} title="Past paper questions">
        <table className="aos-table compact">
          <thead>
            <tr>
              <th>Year</th>
              <th>Paper</th>
              <th>Marks</th>
              <th>Difficulty</th>
            </tr>
          </thead>
          <tbody>
            {b.pastQuestions.map((q, i) => (
              <tr key={i}>
                <td>{q.year}</td>
                <td className="aos-td-strong">{q.paper}</td>
                <td>{q.marks}</td>
                <td>
                  <Badge
                    tone={
                      q.difficulty === "Hard"
                        ? "red"
                        : q.difficulty === "Medium"
                        ? "amber"
                        : "green"
                    }
                  >
                    {q.difficulty}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section n={6} title="Common mistakes">
        <ul className="aos-bk-list">
          {b.mistakes.map((m, i) => (
            <li key={i}>
              <Icon name="x" size={14} style={{ color: "var(--danger)" }} />
              {m}
            </li>
          ))}
        </ul>
      </Section>

      <Section n={7} title="Examiner advice">
        <div className="aos-bk-advice">
          {b.advice.map((a, i) => (
            <div key={i} className="aos-bk-quote">
              <Icon name="quote" size={14} style={{ color: "var(--warn)" }} />
              {a}
            </div>
          ))}
        </div>
      </Section>

      <Section n={8} title="Difficulty ladder">
        <div className="aos-bk-ladder">
          {b.ladder.map((l, i) => (
            <div key={i} className="aos-bk-rung">
              <div className="aos-bk-rungdots">
                {[1, 2, 3, 4, 5].map((d) => (
                  <span key={d} className={d <= l.level ? "on" : ""} />
                ))}
              </div>
              <span>{l.label}</span>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

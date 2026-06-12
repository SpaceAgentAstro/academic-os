"use client";

import { Badge, Button, Card, Icon, SectionTitle } from "@/components/ui";
import { reviewQuestion } from "@/lib/data";
import type { Route } from "@/lib/types";

export function QuestionReview({ go }: { go: (r: Route) => void }) {
  const q = reviewQuestion;
  return (
    <div className="aos-page">
      <div className="aos-page-head">
        <h1>
          {q.id.split("-")[1]} · {q.paper}
        </h1>
        <p className="aos-page-sub">
          {q.topic} · {q.marks} marks
        </p>
        <div className="aos-result-strip">
          <span>
            Your result{" "}
            <strong style={{ color: "var(--warn)" }}>
              {q.yourScore}/{q.marks}
            </strong>
          </span>
          <span className="aos-sep">·</span>
          <span>
            Confidence <strong>{q.confidence}/5</strong>
          </span>
          <span className="aos-sep">·</span>
          <span>
            Time <strong>{q.time}</strong>
          </span>
        </div>
      </div>

      <div className="aos-review-grid">
        {/* Col 1 — question */}
        <Card>
          <SectionTitle>Question</SectionTitle>
          <p className="aos-mark-qtext">{q.text}</p>
          <div className="aos-diagram">
            <Icon name="circuit-capacitor" size={22} style={{ color: "var(--text-3)" }} />
            <span>Circuit diagram</span>
          </div>
          <div className="aos-marks-break">
            <span className="aos-mb-label">Marks breakdown</span>
            {q.markscheme.map((m, i) => (
              <div key={i} className="aos-mb-row">
                <Badge tone="primary">{m.code}</Badge>
                <span>1 mark</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Col 2 — your answer */}
        <Card>
          <SectionTitle>Your answer</SectionTitle>
          <div className="aos-answer-img">
            <Icon name="photo" size={20} style={{ color: "var(--text-3)" }} />
            <span>answer_q8b.jpg</span>
          </div>
          <div className="aos-ocr-box">
            <span className="aos-ocr-tag">OCR extracted</span>
            V = V₀e^(−t/RC); 3 = 12e^(−t/RC); ln(3/12) = t/RC; t = RC·ln(0.25)…
          </div>
          <SectionTitle>Step comparison</SectionTitle>
          <div className="aos-steps">
            {q.steps.map((st, i) => (
              <div key={i} className={`aos-step ${st.ok ? "ok" : "bad"}`}>
                <Icon
                  name={st.ok ? "check" : "x"}
                  size={15}
                  style={{ color: st.ok ? "var(--st-master-fg)" : "var(--st-fail-fg)" }}
                />
                <div>
                  <div className="aos-step-label">
                    Step {i + 1}: {st.label}
                  </div>
                  {st.note && <div className="aos-step-note">{st.note}</div>}
                </div>
              </div>
            ))}
          </div>
          <div className="aos-breakpoint">
            <Icon name="map-pin" size={14} /> Breakdown identified at{" "}
            <strong>Step 3 — sign error</strong>
          </div>
        </Card>

        {/* Col 3 — intelligence */}
        <Card>
          <SectionTitle>Intelligence</SectionTitle>
          <div className="aos-intel-block">
            <div className="aos-intel-label">Official markscheme</div>
            <div className="aos-scheme">
              {q.markscheme.map((m, i) => (
                <div key={i} className="aos-scheme-row">
                  <span className="aos-scheme-code">{m.code}</span>
                  <span className="aos-scheme-text">{m.text}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="aos-examiner-note">
            <Icon name="alert-triangle" size={15} />
            <span>{q.examiner}</span>
          </div>
          <div className="aos-intel-block">
            <div className="aos-intel-label">Mistake classification</div>
            <div className="aos-tags" style={{ marginTop: 6 }}>
              <span className="aos-tag sel">Sign error</span>
              <span className="aos-tag sel">Logarithms</span>
            </div>
          </div>
          <div className="aos-intel-block">
            <div className="aos-intel-label">Similar questions</div>
            {q.similar.map((s) => (
              <div
                key={s.id}
                className="aos-similar"
                onClick={() => go("timer")}
              >
                <Icon name="file-text" size={14} style={{ color: "var(--text-3)" }} />
                {s.label}
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="aos-review-actions">
        <Button variant="primary" icon="refresh" onClick={() => go("timer")}>
          Attempt again
        </Button>
        <Button variant="ghost" icon="bookmark" onClick={() => go("weaknesses")}>
          Add to revision list
        </Button>
        <Button variant="ghost" icon="sparkles" onClick={() => go("tutor")}>
          Generate similar question
        </Button>
      </div>
    </div>
  );
}

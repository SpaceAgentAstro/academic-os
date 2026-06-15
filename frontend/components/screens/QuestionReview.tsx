"use client";

import { Badge, Button, Card, EmptyState, ErrorState, Icon, Loading, SectionTitle } from "@/components/ui";
import { subjectName } from "@/lib/data";
import { getQuestion } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import type { Route } from "@/lib/types";
import type { AppSession } from "@/components/ClientLayout";

const DIFFICULTY = ["", "Recall", "Standard", "Multi-step", "Advanced", "Examiner trap"];

export function QuestionReview({ go, session }: { go: (r: Route) => void; session: AppSession }) {
  const qid = session.questionId;

  if (!qid) {
    return (
      <div className="aos-page aos-narrow">
        <EmptyState
          icon="zoom-question"
          title="No question selected"
          sub="Open a question from the marking screen or the daily briefing to see its full intelligence package."
        />
        <div style={{ marginTop: 14, textAlign: "center" }}>
          <Button variant="primary" onClick={() => go("briefing")}>Go to briefing</Button>
        </div>
      </div>
    );
  }
  return <QuestionDetailView go={go} session={session} qid={qid} />;
}

function QuestionDetailView({
  go, session, qid,
}: {
  go: (r: Route) => void;
  session: AppSession;
  qid: string;
}) {
  const { data: q, loading, error, retry } = useFetch(() => getQuestion(qid), [qid]);

  if (loading) return <div className="aos-page aos-narrow"><Loading label="Loading question intelligence…" /></div>;
  if (error || !q) {
    return <div className="aos-page aos-narrow"><ErrorState message={error ?? "Question not found"} retry={retry} /></div>;
  }

  const lastAttempt = q.previous_attempts[0];

  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head">
        <h1>Q{q.question_number} · {q.paper.code} {q.paper.session}</h1>
        <p className="aos-page-sub">
          {subjectName(q.paper.subject)} {q.paper.unit}
          {q.topic && q.topic !== "Unknown" && <> · {q.topic}</>} · {q.marks} marks ·{" "}
          <Badge tone={q.difficulty >= 4 ? "red" : "amber"}>{DIFFICULTY[q.difficulty] ?? "Unrated"}</Badge>
        </p>
      </div>

      <Card>
        <SectionTitle>Question</SectionTitle>
        <p className="aos-mark-qtext" style={{ whiteSpace: "pre-wrap" }}>
          {(q.question_text ?? "").trim() || "Question text was not extracted."}
        </p>
        {q.command_word && (
          <div style={{ marginTop: 8 }}>
            <Badge tone="primary">Command word: {q.command_word}</Badge>
          </div>
        )}
      </Card>

      {lastAttempt && (
        <Card>
          <SectionTitle>Your last attempt</SectionTitle>
          <div className="aos-pw-stats">
            <div>
              <span className="aos-pw-num">
                {lastAttempt.marks_awarded}/{lastAttempt.marks_available}
              </span>
              <span>marks</span>
            </div>
            <div>
              <span className="aos-pw-num">{lastAttempt.confidence ?? "—"}</span>
              <span>confidence</span>
            </div>
            <div>
              <span className="aos-pw-num">
                {new Date(lastAttempt.created_at).toLocaleDateString("en-GB")}
              </span>
              <span>attempted</span>
            </div>
          </div>
          {lastAttempt.mistakes.length > 0 && (
            <div style={{ marginTop: 10 }}>
              {lastAttempt.mistakes.map((m) => (
                <Badge key={m} tone="red" style={{ marginRight: 6 }}>{m}</Badge>
              ))}
            </div>
          )}
          {lastAttempt.notes && (
            <p className="aos-muted" style={{ marginTop: 8, fontSize: 13 }}>{lastAttempt.notes}</p>
          )}
        </Card>
      )}

      <Card>
        <SectionTitle>Markscheme</SectionTitle>
        <div className="aos-scheme">
          {q.markscheme.length === 0 ? (
            <span className="aos-muted">No markscheme extracted for this question yet.</span>
          ) : (
            q.markscheme.map((m, i) => (
              <div key={i} className="aos-scheme-row">
                <span className="aos-scheme-code">{m.code}</span>
                <span className="aos-scheme-text">
                  {m.text}
                  {m.conditionality && <span className="aos-muted"> ({m.conditionality})</span>}
                </span>
              </div>
            ))
          )}
        </div>
      </Card>

      {(q.examiner_observations.length > 0 || q.misconceptions.length > 0) && (
        <Card>
          <SectionTitle>Examiner intelligence</SectionTitle>
          {q.examiner_observations.map((o, i) => (
            <div key={`o${i}`} className="aos-examiner-note" style={{ marginBottom: 8 }}>
              <Icon name="alert-triangle" size={15} />
              <span><strong>{o.observation_type}:</strong> {o.description}</span>
            </div>
          ))}
          {q.misconceptions.map((m, i) => (
            <div key={`m${i}`} className="aos-examiner-note" style={{ marginBottom: 8 }}>
              <Icon name="bulb" size={15} />
              <span>
                <strong>Misconception ({m.frequency}× seen):</strong> {m.description}
              </span>
            </div>
          ))}
        </Card>
      )}

      {q.similar_questions.length > 0 && (
        <Card pad={false}>
          <SectionTitle>Similar questions on {q.topic}</SectionTitle>
          <div className="aos-list">
            {q.similar_questions.map((s) => (
              <div
                key={s.id}
                className="aos-paper-row"
                onClick={() => session.setQuestionId(s.id)}
              >
                <div className="aos-paper-code">{s.label}</div>
                <Icon name="arrow-right" size={15} style={{ color: "var(--text-3)" }} />
              </div>
            ))}
          </div>
        </Card>
      )}

      <div style={{ display: "flex", gap: 10 }}>
        <Button variant="primary" icon="player-play" onClick={() => go("timer")}>
          Practise this paper
        </Button>
        <Button variant="ghost" onClick={() => go("marking")}>Back to marking</Button>
      </div>
    </div>
  );
}

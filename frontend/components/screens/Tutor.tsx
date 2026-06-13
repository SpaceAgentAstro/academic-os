"use client";

import { EmptyState } from "@/components/ui";

export function Tutor() {
  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head">
        <h1>AI Tutor</h1>
        <p className="aos-page-sub">Personalised explanations grounded in your attempt history</p>
      </div>
      <EmptyState
        icon="message-chatbot"
        title="Tutor is not available yet"
        sub="The AI tutor needs a backend chat endpoint with an ANTHROPIC_API_KEY configured. Nothing is shown here until it can answer from your real data."
      />
    </div>
  );
}

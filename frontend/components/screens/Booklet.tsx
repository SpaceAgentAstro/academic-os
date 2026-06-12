"use client";

import { EmptyState } from "@/components/ui";

export function Booklet() {
  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head">
        <h1>Revision booklets</h1>
        <p className="aos-page-sub">Topic booklets built from your real question bank and weaknesses</p>
      </div>
      <EmptyState
        icon="notebook"
        title="Booklet generation is not available yet"
        sub="Booklets will be assembled from real markschemes, examiner advice, and past questions for a chosen topic. The generation endpoint has not been built — no placeholder content is shown."
      />
    </div>
  );
}

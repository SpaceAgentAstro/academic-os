"use client";

import { type ReactNode } from "react";
import { Icon } from "@/components/ui";
import type { Route } from "@/lib/types";

const ROUTE_LABEL: Record<Route, [string, string]> = {
  home:       ["Overview", "Home"],
  briefing:   ["Overview", "Daily briefing"],
  timer:      ["Study", "Exam timer"],
  marking:    ["Study", "Marking"],
  subjects:   ["Study", "Subjects"],
  questions:  ["Study", "Question review"],
  tutor:      ["Study", "AI tutor"],
  booklets:   ["Study", "Topic booklet"],
  analytics:  ["Analytics", "Analytics"],
  weaknesses: ["Analytics", "Weakness centre"],
  university: ["University", "Readiness"],
  settings:   ["Settings", "Settings"],
};

export function TopBar({
  route,
  setOpen,
  actions,
}: {
  route: Route;
  setOpen: (v: boolean) => void;
  actions?: ReactNode;
}) {
  const [section, title] = ROUTE_LABEL[route] ?? ["", ""];
  return (
    <header className="aos-topbar">
      <div className="aos-topbar-left">
        <button className="aos-burger" onClick={() => setOpen(true)}>
          <Icon name="menu-2" size={20} />
        </button>
        <div className="aos-crumb">
          <span className="aos-crumb-1">{section}</span>
          <Icon name="chevron-right" size={14} style={{ color: "var(--text-3)" }} />
          <span className="aos-crumb-2">{title}</span>
        </div>
      </div>
      <div className="aos-topbar-right">{actions}</div>
    </header>
  );
}

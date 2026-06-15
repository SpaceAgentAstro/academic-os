"use client";

import { Icon } from "@/components/ui";
import type { Route } from "@/lib/types";

const LOGO = (
  <svg viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: 20, height: 20 }}>
    <rect x="3" y="10" width="3" height="7" rx="1" fill="white" />
    <rect x="8.5" y="6" width="3" height="11" rx="1" fill="white" />
    <rect x="14" y="2" width="3" height="15" rx="1" fill="white" />
    <circle cx="4.5" cy="7" r="1.5" fill="#85B7EB" />
    <circle cx="10" cy="3" r="1.5" fill="#85B7EB" />
  </svg>
);

const NAV = [
  {
    group: "Overview",
    items: [
      { id: "home" as Route, label: "Home", icon: "layout-dashboard" },
      { id: "briefing" as Route, label: "Daily briefing", icon: "send" },
    ],
  },
  {
    group: "Study",
    items: [
      { id: "timer" as Route, label: "Exam timer", icon: "clock" },
      { id: "marking" as Route, label: "Marking", icon: "checkbox" },
      { id: "subjects" as Route, label: "Subjects", icon: "books" },
      { id: "questions" as Route, label: "Question review", icon: "file-text" },
      { id: "tutor" as Route, label: "AI tutor", icon: "brain" },
      { id: "booklets" as Route, label: "Topic booklet", icon: "notebook" },
    ],
  },
  {
    group: "Analytics",
    items: [
      { id: "analytics" as Route, label: "Analytics", icon: "chart-histogram" },
      { id: "weaknesses" as Route, label: "Weakness centre", icon: "alert-triangle" },
    ],
  },
  {
    group: "University",
    items: [{ id: "university" as Route, label: "Readiness", icon: "building-bank" }],
  },
  {
    group: "Settings",
    items: [{ id: "settings" as Route, label: "Settings", icon: "settings" }],
  },
];

export function Sidebar({
  route,
  go,
  open,
  setOpen,
  dark,
  toggleDark,
}: {
  route: Route;
  go: (r: Route) => void;
  open: boolean;
  setOpen: (v: boolean) => void;
  dark: boolean;
  toggleDark: () => void;
}) {
  return (
    <>
      <div className={`aos-scrim ${open ? "show" : ""}`} onClick={() => setOpen(false)} />
      <aside className={`aos-sidebar ${open ? "open" : ""}`}>
        <div className="aos-brand">
          <div className="aos-logo">{LOGO}</div>
          <div>
            <div className="aos-brand-name">AcademicOS</div>
          </div>
        </div>

        <nav className="aos-nav">
          {NAV.map((sec) => (
            <div key={sec.group} className="aos-nav-group">
              <div className="aos-nav-label">{sec.group}</div>
              {sec.items.map((it) => (
                <button
                  key={it.id}
                  className={`aos-nav-item ${route === it.id ? "active" : ""}`}
                  onClick={() => { go(it.id); setOpen(false); }}
                >
                  <Icon name={it.icon} size={18} />
                  <span>{it.label}</span>
                </button>
              ))}
            </div>
          ))}
        </nav>

        <div className="aos-side-foot">
          <div className="aos-avatar">MM</div>
          <div className="aos-foot-id">
            <div className="aos-foot-name">Mouad Maamma</div>
            {/* Grades must come from real data, never fabricated (LOGIC-007).
                Until a per-subject grade summary is wired in, show the board. */}
            <div className="aos-foot-grades">Pearson Edexcel IAL</div>
          </div>
          <button
            className="aos-theme-toggle"
            onClick={toggleDark}
            title={dark ? "Light mode" : "Dark mode"}
          >
            <Icon name={dark ? "sun" : "moon"} size={15} />
          </button>
        </div>
      </aside>
    </>
  );
}

"use client";

import { useState, useEffect, type ReactNode } from "react";
import { Sidebar } from "@/components/shell/Sidebar";
import { TopBar } from "@/components/shell/TopBar";
import { Home } from "@/components/screens/Home";
import { Briefing } from "@/components/screens/Briefing";
import { Timer } from "@/components/screens/Timer";
import { Marking } from "@/components/screens/Marking";
import { Subjects } from "@/components/screens/Subjects";
import { QuestionReview } from "@/components/screens/QuestionReview";
import { Tutor } from "@/components/screens/Tutor";
import { Booklet } from "@/components/screens/Booklet";
import { Analytics } from "@/components/screens/Analytics";
import { Weaknesses } from "@/components/screens/Weaknesses";
import { University } from "@/components/screens/University";
import { Settings } from "@/components/screens/Settings";
import type { Route } from "@/lib/types";

// Shared cross-screen state: which paper/session is live, which question to deep-dive
export interface AppSession {
  paperId: string | null;
  sessionId: number | null;
  questionId: string | null;
  setPaperId: (id: string | null) => void;
  setSessionId: (id: number | null) => void;
  setQuestionId: (id: string | null) => void;
}

function Btn({ children, icon, primary, onClick }: {
  children: ReactNode;
  icon?: string;
  primary?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      className={`aos-btn ${primary ? "aos-btn-primary" : "aos-btn-ghost"} aos-btn-md`}
      onClick={onClick}
    >
      {icon && <i className={`ti ti-${icon}`} style={{ fontSize: 16 }} />}
      {children}
    </button>
  );
}

const ROUTES: Route[] = [
  "home", "briefing", "timer", "marking", "subjects", "questions",
  "tutor", "booklets", "analytics", "weaknesses", "university", "settings",
];

function routeFromHash(): Route {
  if (typeof window === "undefined") return "home";
  const h = window.location.hash.replace(/^#\/?/, "") as Route;
  return ROUTES.includes(h) ? h : "home";
}

export function ClientLayout() {
  // Initialise route from the URL hash so refresh/back/forward and deep links
  // work instead of always resetting to home (RT-019).
  const [route, setRoute] = useState<Route>("home");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  // Theme is applied before paint by the blocking script in app/layout.tsx;
  // read the resulting attribute here so React state matches (no FOUC, RT-015).
  const [dark, setDark] = useState<boolean>(() =>
    typeof document !== "undefined" && document.documentElement.dataset.theme === "dark"
  );
  const [paperId, setPaperId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [questionId, setQuestionId] = useState<string | null>(null);

  // Sync route to the URL hash and recover active session/paper across reloads.
  useEffect(() => {
    setRoute(routeFromHash());
    try {
      const saved = sessionStorage.getItem("aos-session");
      if (saved) {
        const s = JSON.parse(saved);
        if (s.paperId) setPaperId(s.paperId);
        if (s.sessionId != null) setSessionId(s.sessionId);
        if (s.questionId) setQuestionId(s.questionId);
      }
    } catch { /* ignore corrupt storage */ }
    const onHash = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    try {
      sessionStorage.setItem("aos-session", JSON.stringify({ paperId, sessionId, questionId }));
    } catch { /* storage may be unavailable */ }
  }, [paperId, sessionId, questionId]);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    try {
      localStorage.setItem("aos-theme", dark ? "dark" : "light");
    } catch { /* ignore */ }
  }, [dark]);

  const go = (r: Route) => {
    if (typeof window !== "undefined") window.location.hash = `#/${r}`;
    setRoute(r);
    setSidebarOpen(false);
  };

  const toggleDark = () => setDark((d) => !d);

  const session: AppSession = {
    paperId, sessionId, questionId,
    setPaperId, setSessionId, setQuestionId,
  };

  const TOP_ACTIONS: Partial<Record<Route, ReactNode>> = {
    home:     <Btn icon="player-play" primary onClick={() => go("timer")}>Start paper</Btn>,
    timer:    sessionId != null
      ? <Btn icon="checkbox" onClick={() => go("marking")}>Go to marking</Btn>
      : undefined,
    marking:  <Btn icon="player-play" primary onClick={() => go("timer")}>New session</Btn>,
    subjects: <Btn icon="player-play" primary onClick={() => go("timer")}>Start paper</Btn>,
  };

  function Screen() {
    switch (route) {
      case "home":       return <Home go={go} session={session} />;
      case "briefing":   return <Briefing go={go} session={session} />;
      case "timer":      return <Timer go={go} session={session} />;
      case "marking":    return <Marking go={go} session={session} />;
      case "subjects":   return <Subjects go={go} session={session} />;
      case "questions":  return <QuestionReview go={go} session={session} />;
      case "tutor":      return <Tutor />;
      case "booklets":   return <Booklet />;
      case "analytics":  return <Analytics go={go} session={session} />;
      case "weaknesses": return <Weaknesses go={go} />;
      case "university": return <University />;
      case "settings":   return <Settings dark={dark} toggleDark={toggleDark} />;
      default:           return <Home go={go} session={session} />;
    }
  }

  return (
    <div className="aos-app">
      <Sidebar
        route={route}
        go={go}
        open={sidebarOpen}
        setOpen={setSidebarOpen}
        dark={dark}
        toggleDark={toggleDark}
      />
      <div className="aos-main">
        <TopBar route={route} setOpen={setSidebarOpen} actions={TOP_ACTIONS[route]} />
        <main className="aos-content">
          <Screen />
        </main>
      </div>
    </div>
  );
}

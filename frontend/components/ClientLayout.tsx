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

function routeFromHash(): Route | null {
  if (typeof window === "undefined") return null;
  const h = window.location.hash.replace(/^#\/?/, "") as Route;
  return ROUTES.includes(h) ? h : null;
}

export function ClientLayout() {
  const [route, setRoute] = useState<Route>("home");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const [paperId, setPaperId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [questionId, setQuestionId] = useState<string | null>(null);

  useEffect(() => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(prefersDark);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  }, [dark]);

  // Recover route + in-progress session context on load, and keep the URL hash
  // in sync so refresh, deep-links, and back/forward all work (RT-019).
  useEffect(() => {
    const stored = sessionStorage.getItem("aos:session");
    if (stored) {
      try {
        const s = JSON.parse(stored);
        if (s.paperId) setPaperId(s.paperId);
        if (s.sessionId) setSessionId(s.sessionId);
        if (s.questionId) setQuestionId(s.questionId);
      } catch {
        /* ignore corrupt state */
      }
    }
    const initial = routeFromHash();
    if (initial) setRoute(initial);
    const onHash = () => {
      const r = routeFromHash();
      if (r) setRoute(r);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    sessionStorage.setItem(
      "aos:session",
      JSON.stringify({ paperId, sessionId, questionId }),
    );
  }, [paperId, sessionId, questionId]);

  const go = (r: Route) => {
    setRoute(r);
    setSidebarOpen(false);
    if (typeof window !== "undefined" && routeFromHash() !== r) {
      window.location.hash = `#/${r}`;
    }
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

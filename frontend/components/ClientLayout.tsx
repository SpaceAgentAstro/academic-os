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
import type { Route, SessionParams } from "@/lib/types";

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

export function ClientLayout() {
  const [route, setRoute] = useState<Route>("home");
  const [session, setSession] = useState<SessionParams>({});
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(prefersDark);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  }, [dark]);

  const go = (r: Route, params?: SessionParams) => {
    setRoute(r);
    if (params) setSession((prev) => ({ ...prev, ...params }));
    setSidebarOpen(false);
  };

  const toggleDark = () => setDark((d) => !d);

  const TOP_ACTIONS: Partial<Record<Route, ReactNode>> = {
    home:       <Btn icon="player-play" primary onClick={() => go("analytics")}>Start paper</Btn>,
    timer:      <Btn icon="checkbox" onClick={() => go("marking", session)}>Go to marking</Btn>,
    marking:    <Btn icon="player-play" primary onClick={() => go("analytics")}>New session</Btn>,
    subjects:   <Btn icon="player-play" primary onClick={() => go("analytics")}>Start paper</Btn>,
    weaknesses: <Btn icon="notebook" primary onClick={() => go("booklets")}>Generate booklet</Btn>,
    briefing:   <Btn icon="send" onClick={() => go("settings")}>Briefing settings</Btn>,
    tutor:      <Btn icon="plus" onClick={() => go("tutor")}>New chat</Btn>,
    booklets:   <Btn icon="download" primary>Download PDF</Btn>,
  };

  function Screen() {
    switch (route) {
      case "home":       return <Home go={go} greeting="Good morning, Mouad Maamma." />;
      case "briefing":   return <Briefing go={go} />;
      case "timer":      return <Timer go={go} session={session} />;
      case "marking":    return <Marking go={go} session={session} />;
      case "subjects":   return <Subjects go={go} />;
      case "questions":  return <QuestionReview go={go} />;
      case "tutor":      return <Tutor />;
      case "booklets":   return <Booklet />;
      case "analytics":  return <Analytics go={go} />;
      case "weaknesses": return <Weaknesses go={go} />;
      case "university": return <University />;
      case "settings":   return <Settings dark={dark} toggleDark={toggleDark} />;
      default:           return <Home go={go} greeting="Good morning, Mouad Maamma." />;
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

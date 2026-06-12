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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dark, setDark] = useState(false);
  const [greeting, setGreeting] = useState("Good morning, Mouad Maamma.");

  useEffect(() => {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setDark(prefersDark);
    const h = new Date().getHours();
    const word = h < 12 ? "morning" : h < 18 ? "afternoon" : "evening";
    setGreeting(`Good ${word}, Mouad Maamma.`);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
  }, [dark]);

  const go = (r: Route) => {
    setRoute(r);
    setSidebarOpen(false);
  };

  const toggleDark = () => setDark((d) => !d);

  const TOP_ACTIONS: Partial<Record<Route, ReactNode>> = {
    home:       <Btn icon="player-play" primary onClick={() => go("timer")}>Start paper</Btn>,
    timer:      <Btn icon="checkbox" onClick={() => go("marking")}>Go to marking</Btn>,
    marking:    <Btn icon="player-play" primary onClick={() => go("timer")}>New session</Btn>,
    subjects:   <Btn icon="player-play" primary onClick={() => go("timer")}>Start paper</Btn>,
    weaknesses: <Btn icon="notebook" primary onClick={() => go("booklets")}>Generate booklet</Btn>,
    briefing:   <Btn icon="send" onClick={() => go("settings")}>Briefing settings</Btn>,
    tutor:      <Btn icon="plus" onClick={() => go("tutor")}>New chat</Btn>,
    booklets:   <Btn icon="download" primary onClick={() => window.print()}>Download PDF</Btn>,
  };

  // Rendered via a plain function call (not <Screen />) so the active screen
  // keeps its state when this layout re-renders (sidebar/theme toggles).
  function renderScreen() {
    switch (route) {
      case "home":       return <Home go={go} greeting={greeting} />;
      case "briefing":   return <Briefing go={go} />;
      case "timer":      return <Timer go={go} />;
      case "marking":    return <Marking go={go} />;
      case "subjects":   return <Subjects go={go} />;
      case "questions":  return <QuestionReview go={go} />;
      case "tutor":      return <Tutor />;
      case "booklets":   return <Booklet />;
      case "analytics":  return <Analytics go={go} />;
      case "weaknesses": return <Weaknesses go={go} />;
      case "university": return <University />;
      case "settings":   return <Settings dark={dark} toggleDark={toggleDark} />;
      default:           return <Home go={go} greeting={greeting} />;
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
          {renderScreen()}
        </main>
      </div>
    </div>
  );
}

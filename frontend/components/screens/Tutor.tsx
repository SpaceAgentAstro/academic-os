"use client";

import { useState, useRef, useEffect } from "react";
import { Card, Icon } from "@/components/ui";
import { tutorSeed } from "@/lib/data";

const CHIPS = [
  "Explain this topic",
  "Generate harder question",
  "Show examiner traps",
  "Quiz me",
];

const REPLIES: Record<string, string> = {
  "Explain this topic":
    "Capacitor discharge follows V = V₀e^(−t/RC). The key intuition: every time constant τ = RC, the voltage falls to 37% of its previous value. Your 14 attempts show you understand the model — the slip is purely algebraic at the logarithm step.",
  "Generate harder question":
    "Try this (8 marks): A 2200 μF capacitor charged to 9.0 V discharges through an unknown resistor. After 4.0 s the p.d. is 5.4 V. (a) Find R. (b) Find the energy dissipated in the first 4.0 s. Watch the sign when you take ln(5.4/9.0).",
  "Show examiner traps":
    "Three traps flagged for capacitance: (1) dropping the negative sign in ln — your recurring error, seen 14×. (2) μF vs F conversion in substitution. (3) confusing τ with half-life. Reports from Jun 2023, Jan 2022 and Jun 2021 all penalise (1).",
  "Quiz me":
    "Quick check: a capacitor discharges to 1/e of its initial charge. How many time constants have elapsed? (Reply with a number.)",
};

function LogoMini() {
  return (
    <svg viewBox="0 0 20 20" style={{ width: 14, height: 14 }}>
      <rect x="3" y="10" width="3" height="7" rx="1" fill="#fff" />
      <rect x="8.5" y="6" width="3" height="11" rx="1" fill="#fff" />
      <rect x="14" y="2" width="3" height="15" rx="1" fill="#fff" />
    </svg>
  );
}

export function Tutor() {
  const [msgs, setMsgs] = useState<{ role: "user" | "tutor"; text: string }[]>(tutorSeed);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [msgs, typing]);

  const send = (text?: string) => {
    const t = (text ?? input).trim();
    if (!t) return;
    setMsgs((m) => [...m, { role: "user", text: t }]);
    setInput("");
    setTyping(true);
    setTimeout(() => {
      const reply =
        REPLIES[t] ??
        "Looking at your attempt history, the pattern points back to the logarithm rearrangement. Write ln(Q/Q₀) = −t/RC and isolate t as RC·ln(Q₀/Q) — flipping the ratio absorbs the negative sign cleanly.";
      setMsgs((m) => [...m, { role: "tutor", text: reply }]);
      setTyping(false);
    }, 850);
  };

  return (
    <div className="aos-page aos-tutor-page">
      <div className="aos-page-head">
        <h1>AI Tutor</h1>
        <p className="aos-page-sub">Capacitance · Unit 5 · Physics</p>
      </div>
      <div className="aos-tutor-context">
        <Icon name="bulb" size={15} style={{ color: "var(--primary)" }} />
        <span>
          Tutor knows: your <strong>14 mistakes</strong> on discharging equations, your{" "}
          <strong>sign-error pattern</strong>, and your confidence calibration.
        </span>
      </div>

      <Card className="aos-chat-card" pad={false}>
        <div className="aos-chat" ref={chatRef}>
          {msgs.map((m, i) => (
            <div key={i} className={`aos-msg ${m.role}`}>
              {m.role === "tutor" && (
                <div className="aos-msg-av">
                  <LogoMini />
                </div>
              )}
              <div className="aos-bubble">{m.text}</div>
            </div>
          ))}
          {typing && (
            <div className="aos-msg tutor">
              <div className="aos-msg-av">
                <LogoMini />
              </div>
              <div className="aos-bubble">
                <div className="aos-typing">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="aos-chat-chips">
          {CHIPS.map((c) => (
            <button key={c} className="aos-chip" onClick={() => send(c)}>
              {c}
            </button>
          ))}
        </div>
        <div className="aos-chat-input">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Ask about capacitor discharge…"
          />
          <button className="aos-send" onClick={() => send()}>
            <Icon name="send" size={16} />
          </button>
        </div>
      </Card>
    </div>
  );
}

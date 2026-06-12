"use client";

import { useState, type ReactNode } from "react";
import { Card, Icon, Toggle } from "@/components/ui";
import { subjects } from "@/lib/data";
import { useStatus } from "@/lib/hooks";
import type { Grade } from "@/lib/types";

function Group({ icon, title, children }: { icon: string; title: string; children: ReactNode }) {
  return (
    <Card pad={false} className="aos-set-group">
      <div className="aos-set-head">
        <Icon name={icon} size={16} style={{ color: "var(--primary)" }} />
        {title}
      </div>
      {children}
    </Card>
  );
}

function Row({ label, children }: { label: string; children?: ReactNode }) {
  return (
    <div className="aos-set-row">
      <span className="aos-set-label">{label}</span>
      <div className="aos-set-ctrl">{children}</div>
    </div>
  );
}

const FALLBACK_DBS: [string, string, boolean][] = [
  ["question_bank.db", "2,260 questions", true],
  ["examiner_reports.db", "184 reports", true],
  ["markscheme.db", "2,260 schemes", true],
  ["progress.db", "847 sessions", true],
];

export function Settings({ dark, toggleDark }: { dark?: boolean; toggleDark?: () => void }) {
  const [time, setTime] = useState("07:00");
  const [targets, setTargets] = useState<Record<string, Grade>>(() =>
    Object.fromEntries(subjects.map((s) => [s.id, s.predicted]))
  );
  const status = useStatus();

  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head">
        <h1>Settings</h1>
        <p className="aos-page-sub">Configure your academic operating system</p>
      </div>

      <Group icon="user" title="Profile">
        <Row label="Name">
          <input className="aos-input" defaultValue="Mouad Maamma" />
        </Row>
        <Row label="Subjects">
          <span className="aos-muted">Physics · Maths · Further Maths · Chemistry · CS</span>
        </Row>
        <Row label="Exam session">
          <span className="aos-badge tone-primary">June 2026</span>
        </Row>
      </Group>

      <Group icon="bell" title="Notifications">
        <Row label="Telegram briefing time">
          <input
            className="aos-input narrow"
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
        </Row>
        <Row label="Spaced-repetition reminders"><Toggle on /></Row>
        <Row label="Examiner-trap alerts"><Toggle on /></Row>
      </Group>

      <Group icon="target" title="Targets">
        {subjects.map((s) => (
          <Row key={s.id} label={s.name}>
            <div className="aos-target-grades">
              {(["A*", "A", "B"] as const).map((g) => (
                <button
                  key={g}
                  className={`aos-tgt ${targets[s.id] === g ? "sel" : ""}`}
                  onClick={() => setTargets((t) => ({ ...t, [s.id]: g }))}
                >
                  {g}
                </button>
              ))}
            </div>
          </Row>
        ))}
      </Group>

      <Group icon="refresh" title="Spaced repetition">
        <Row label="Algorithm"><span className="aos-muted">SM-2 (modified)</span></Row>
        <Row label="Daily review cap">
          <input className="aos-input narrow" defaultValue="20" />
        </Row>
        <Row label="Review difficult items first"><Toggle on /></Row>
      </Group>

      <Group icon="database" title="Data">
        {(status?.databases
          ? status.databases.map((db) => [db.name, db.label, db.ok] as [string, string, boolean])
          : FALLBACK_DBS
        ).map(([n, m, ok]) => (
          <Row key={n} label={n}>
            <span className="aos-db-status">
              <Icon
                name="circle-check-filled"
                size={15}
                style={{ color: ok ? "var(--accent)" : "var(--danger)" }}
              />
              {m}
            </span>
          </Row>
        ))}
      </Group>

      <Group icon="palette" title="Appearance">
        <Row label="Theme">
          <div className="aos-seg sm">
            <button
              className={!dark ? "active" : ""}
              onClick={() => dark && toggleDark?.()}
            >
              Light
            </button>
            <button
              className={dark ? "active" : ""}
              onClick={() => !dark && toggleDark?.()}
            >
              Dark
            </button>
          </div>
        </Row>
      </Group>
    </div>
  );
}

"use client";

import { type ReactNode } from "react";
import { Card, ErrorState, Icon, Loading } from "@/components/ui";
import { SUBJECT_LABELS } from "@/lib/data";
import { getStatus } from "@/lib/api";
import { useFetch } from "@/lib/hooks";

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

export function Settings({ dark, toggleDark }: { dark?: boolean; toggleDark?: () => void }) {
  const status = useFetch(getStatus);

  return (
    <div className="aos-page aos-narrow">
      <div className="aos-page-head">
        <h1>Settings</h1>
        <p className="aos-page-sub">Configure your academic operating system</p>
      </div>

      <Group icon="user" title="Profile">
        <Row label="Name">
          <span className="aos-muted">Mouad Maamma</span>
        </Row>
        <Row label="Subjects">
          <span className="aos-muted">
            {Object.values(SUBJECT_LABELS).map((s) => s.short).join(" · ")}
          </span>
        </Row>
        <Row label="Exam session">
          <span className="aos-badge tone-primary">June 2026</span>
        </Row>
      </Group>

      <Group icon="bell" title="Notifications">
        <Row label="Telegram briefing time">
          <span className="aos-muted">Set via BRIEFING_TIME in .env</span>
        </Row>
        <Row label="Spaced-repetition reminders">
          <span className="aos-muted">Sent with the daily briefing</span>
        </Row>
        <Row label="Examiner-trap alerts">
          <span className="aos-muted">Included in the daily briefing</span>
        </Row>
      </Group>

      <Group icon="refresh" title="Spaced repetition">
        <Row label="Algorithm"><span className="aos-muted">SM-2 (modified)</span></Row>
        <Row label="Review difficult items first">
          <span className="aos-muted">Default ordering (lowest mastery first)</span>
        </Row>
      </Group>

      <Group icon="database" title="Data">
        {status.loading && (
          <div style={{ padding: 16 }}><Loading label="Checking databases…" /></div>
        )}
        {status.error && (
          <div style={{ padding: 16 }}>
            <ErrorState
              message="Cannot reach the backend — database status unavailable."
              retry={status.retry}
            />
          </div>
        )}
        {status.data?.databases.map((db) => (
          <Row key={db.name} label={db.name}>
            <span className="aos-db-status">
              <Icon
                name={db.ok ? "circle-check-filled" : "alert-circle-filled"}
                size={15}
                style={{ color: db.ok ? "var(--accent)" : "var(--danger)" }}
              />
              {db.label}
            </span>
          </Row>
        ))}
      </Group>

      <Group icon="palette" title="Appearance">
        <Row label="Theme">
          <div className="aos-seg sm">
            <button className={!dark ? "active" : ""} onClick={() => dark && toggleDark?.()}>
              Light
            </button>
            <button className={dark ? "active" : ""} onClick={() => !dark && toggleDark?.()}>
              Dark
            </button>
          </div>
        </Row>
      </Group>
    </div>
  );
}

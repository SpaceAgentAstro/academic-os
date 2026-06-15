"use client";

import { useState, type ReactNode } from "react";
import type { BadgeTone, Grade, MasteryBand } from "@/lib/types";
import { bandColor as computeBandColor, masteryBand } from "@/lib/data";

// ---- Badge ------------------------------------------------------------------
export function Badge({
  children,
  tone = "neutral",
  style,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  style?: React.CSSProperties;
}) {
  return (
    <span className={`aos-badge tone-${tone}`} style={style}>
      {children}
    </span>
  );
}

const gradeClass = (g: Grade) =>
  g === "A*" ? "grade-as"
  : g === "A" ? "grade-a"
  : g === "B" ? "grade-b"
  : g === "C" ? "grade-c"
  : g === "D" ? "grade-d"
  : g === "E" ? "grade-e"
  : "grade-u";

export function GradeBadge({ grade }: { grade: Grade }) {
  return <span className={`aos-badge ${gradeClass(grade)}`}>{grade}</span>;
}

// ---- Card -------------------------------------------------------------------
export function Card({
  children,
  className = "",
  style,
  pad = true,
  onClick,
}: {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  pad?: boolean;
  onClick?: () => void;
}) {
  return (
    <div
      className={`aos-card ${className}`}
      onClick={onClick}
      style={{ padding: pad ? 20 : 0, cursor: onClick ? "pointer" : undefined, ...style }}
    >
      {children}
    </div>
  );
}

// ---- Metric -----------------------------------------------------------------
export function Metric({
  label,
  value,
  sub,
  accent,
  icon,
}: {
  label: string;
  value: ReactNode;
  sub?: string;
  accent?: string;
  icon?: string;
}) {
  return (
    <div className="aos-card aos-metric">
      <div className="aos-metric-top">
        <span className="aos-metric-label">{label}</span>
        {icon && <Icon name={icon} size={16} style={{ color: "var(--text-3)" }} />}
      </div>
      <div className="aos-metric-value" style={accent ? { color: accent } : undefined}>
        {value}
      </div>
      {sub && <div className="aos-metric-sub">{sub}</div>}
    </div>
  );
}

// ---- MasteryBar -------------------------------------------------------------
export function MasteryBar({
  value,
  height = 6,
  showLabel = false,
  band,
}: {
  value: number;
  height?: number;
  showLabel?: boolean;
  band?: MasteryBand;
}) {
  const b = band ?? masteryBand(value);
  return (
    <div className="aos-mbar-wrap">
      <div className="aos-mbar" style={{ height }}>
        <div
          className="aos-mbar-fill"
          style={{ width: `${value}%`, background: computeBandColor(b) }}
        />
      </div>
      {showLabel && (
        <span className="aos-mbar-label" style={{ color: computeBandColor(b) }}>
          {value}%
        </span>
      )}
    </div>
  );
}

// ---- Dot --------------------------------------------------------------------
export function Dot({ level }: { level: "high" | "med" | "low" }) {
  const c =
    level === "high" ? "var(--danger)" : level === "med" ? "var(--warn)" : "var(--accent)";
  return <span className="aos-dot" style={{ background: c }} />;
}

// ---- SectionTitle -----------------------------------------------------------
export function SectionTitle({
  children,
  action,
}: {
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="aos-section-title">
      <span>{children}</span>
      {action}
    </div>
  );
}

// ---- Button -----------------------------------------------------------------
export function Button({
  children,
  variant = "ghost",
  size = "md",
  onClick,
  icon,
  style,
  type,
  disabled,
}: {
  children?: ReactNode;
  variant?: "ghost" | "primary" | "onnavy";
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
  icon?: string;
  style?: React.CSSProperties;
  type?: "button" | "submit";
  disabled?: boolean;
}) {
  return (
    <button
      className={`aos-btn aos-btn-${variant} aos-btn-${size}`}
      onClick={onClick}
      type={type ?? "button"}
      style={style}
      disabled={disabled}
    >
      {icon && <Icon name={icon} size={size === "sm" ? 14 : 16} />}
      {children}
    </button>
  );
}

// ---- Icon (Tabler) ----------------------------------------------------------
export function Icon({
  name,
  size = 18,
  style,
  className,
}: {
  name: string;
  size?: number;
  style?: React.CSSProperties;
  className?: string;
}) {
  return (
    <i
      className={`ti ti-${name} ${className ?? ""}`}
      aria-hidden="true"
      style={{ fontSize: size, lineHeight: 1, ...style }}
    />
  );
}

// ---- Async states -------------------------------------------------------------
export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="aos-card" style={{ padding: 32, display: "flex", alignItems: "center", gap: 12, justifyContent: "center" }}>
      <div className="aos-spinner" />
      <span style={{ color: "var(--text-2)", fontSize: 14 }}>{label}</span>
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="aos-card" style={{ padding: 32, textAlign: "center" }}>
      <Icon name="plug-x" size={28} style={{ color: "var(--danger)" }} />
      <div style={{ fontWeight: 600, marginTop: 10 }}>Could not load data</div>
      <div style={{ color: "var(--text-2)", fontSize: 13, marginTop: 4 }}>{message}</div>
      {retry && (
        <div style={{ marginTop: 14 }}>
          <Button variant="primary" icon="refresh" onClick={retry}>Retry</Button>
        </div>
      )}
    </div>
  );
}

export function EmptyState({ icon = "database-off", title, sub }: { icon?: string; title: string; sub?: string }) {
  return (
    <div className="aos-card" style={{ padding: 32, textAlign: "center" }}>
      <Icon name={icon} size={28} style={{ color: "var(--text-3)" }} />
      <div style={{ fontWeight: 600, marginTop: 10 }}>{title}</div>
      {sub && <div style={{ color: "var(--text-2)", fontSize: 13, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

// ---- Toggle -----------------------------------------------------------------
export function Toggle({
  on: init,
  checked,
  onChange,
  disabled,
}: {
  on?: boolean;
  checked?: boolean;
  onChange?: (v: boolean) => void;
  disabled?: boolean;
}) {
  const controlled = checked !== undefined;
  const [localOn, setLocalOn] = useState(init ?? false);
  const on = controlled ? checked! : localOn;
  const toggle = () => {
    if (disabled) return;
    if (controlled) {
      onChange?.(!on);
    } else {
      setLocalOn((v) => !v);
      onChange?.(!on);
    }
  };
  return (
    <button
      className={`aos-toggle ${on ? "on" : ""}`}
      onClick={toggle}
      disabled={disabled}
      aria-disabled={disabled}
    >
      <span />
    </button>
  );
}

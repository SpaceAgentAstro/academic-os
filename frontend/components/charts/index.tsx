"use client";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line, Bar, Scatter, Doughnut } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
  Filler
);

function getCSSVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// ---- LineChart --------------------------------------------------------------
export function LineChart({
  labels,
  datasets,
  height = 200,
  yMax,
  yMin,
  fmt,
}: {
  labels: (string | number)[];
  datasets: {
    data: number[];
    borderColor?: string;
    backgroundColor?: string;
    pointRadius?: number;
    fill?: boolean;
    label?: string;
  }[];
  height?: number;
  yMax?: number;
  yMin?: number;
  fmt?: (v: number) => string;
}) {
  const navy = getCSSVar("--primary");
  const grid = getCSSVar("--chart-grid");

  const data = {
    labels,
    datasets: datasets.map((d) => ({
      tension: 0.35,
      borderWidth: 1.5,
      borderColor: d.borderColor ?? navy,
      pointRadius: d.pointRadius ?? 0,
      pointHoverRadius: 4,
      pointBackgroundColor: d.borderColor ?? navy,
      fill: d.fill ?? true,
      backgroundColor: d.backgroundColor ?? `${navy}18`,
      label: d.label ?? "",
      data: d.data,
    })),
  };

  return (
    <div style={{ height }}>
      <Line
        data={data}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          plugins: {
            legend: {
              display: datasets.length > 1,
              labels: { boxWidth: 8, boxHeight: 8, usePointStyle: true, padding: 16 },
            },
          },
          scales: {
            x: { grid: { display: false }, ticks: { maxRotation: 0 } },
            y: {
              grid: { color: grid || "rgba(0,0,0,0.05)" },
              border: { display: false },
              min: yMin,
              max: yMax,
              ticks: {
                callback: fmt ? (v) => fmt(v as number) : undefined,
              },
            },
          },
        }}
      />
    </div>
  );
}

// ---- BarChart ---------------------------------------------------------------
export function BarChart({
  labels,
  data: rawData,
  colors,
  height = 220,
  horizontal = false,
  max,
  fmt,
  stacked = false,
  datasets,
}: {
  labels: string[];
  data?: number[];
  colors?: string[];
  height?: number;
  horizontal?: boolean;
  max?: number;
  fmt?: (v: number) => string;
  stacked?: boolean;
  datasets?: {
    label: string;
    data: number[];
    backgroundColor: string;
    borderRadius?: number;
  }[];
}) {
  const navy = getCSSVar("--primary");
  const grid = getCSSVar("--chart-grid");

  const chartData = datasets
    ? { labels, datasets }
    : {
        labels,
        datasets: [
          {
            data: rawData ?? [],
            backgroundColor: colors ?? `${navy}cc`,
            borderRadius: 3,
            barPercentage: 0.78,
            categoryPercentage: 0.78,
            label: "",
          },
        ],
      };

  const gridColor = grid || "rgba(0,0,0,0.05)";

  return (
    <div style={{ height }}>
      <Bar
        data={chartData}
        options={{
          indexAxis: horizontal ? ("y" as const) : ("x" as const),
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          plugins: {
            legend: {
              display: stacked,
              labels: { boxWidth: 8, boxHeight: 8, usePointStyle: true, padding: 16 },
            },
          },
          scales: {
            x: {
              stacked,
              grid: { display: horizontal, color: gridColor },
              border: { display: false },
              max: horizontal ? max : undefined,
              ticks: horizontal && fmt ? { callback: (v) => fmt(v as number) } : {},
            },
            y: {
              stacked,
              grid: { display: !horizontal, color: gridColor },
              border: { display: false },
              max: horizontal ? undefined : max,
              ticks: !horizontal && fmt ? { callback: (v) => fmt(v as number) } : {},
            },
          },
        }}
      />
    </div>
  );
}

// ---- ScatterChart -----------------------------------------------------------
export function ScatterChart({
  points,
  height = 220,
}: {
  points: { x: number; y: number; label: string }[];
  height?: number;
}) {
  const navy = getCSSVar("--primary");
  const grid = getCSSVar("--chart-grid");

  return (
    <div style={{ height }}>
      <Scatter
        data={{
          datasets: [
            {
              data: points,
              backgroundColor: navy,
              pointRadius: 4,
              pointHoverRadius: 6,
            },
          ],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (c) => {
                  const raw = c.raw as { x: number; y: number; label: string };
                  return `${raw.label}: ${raw.x}min, ${raw.y}%`;
                },
              },
            },
          },
          scales: {
            x: {
              title: { display: true, text: "Time (min)" },
              grid: { color: grid || "rgba(0,0,0,0.05)" },
              border: { display: false },
            },
            y: {
              title: { display: true, text: "Score %" },
              min: 40,
              max: 100,
              grid: { color: grid || "rgba(0,0,0,0.05)" },
              border: { display: false },
            },
          },
        }}
      />
    </div>
  );
}

// ---- DonutChart -------------------------------------------------------------
export function DonutChart({
  value,
  color,
  height = 130,
  label,
}: {
  value: number;
  color: string;
  height?: number;
  label?: string;
}) {
  return (
    <div style={{ height, position: "relative" }}>
      <Doughnut
        data={{
          datasets: [
            {
              data: [value, 100 - value],
              backgroundColor: [color, "var(--surface-2)"],
              borderWidth: 0,
            },
          ],
        }}
        options={{
          cutout: "74%",
          responsive: true,
          maintainAspectRatio: false,
          animation: false,
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
        }}
      />
      <div className="aos-donut-center">
        <div className="aos-donut-val" style={{ color }}>
          {value}%
        </div>
        {label && <div className="aos-donut-label">{label}</div>}
      </div>
    </div>
  );
}

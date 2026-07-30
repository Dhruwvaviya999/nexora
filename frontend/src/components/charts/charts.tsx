"use client";

/**
 * Dependency-free SVG charts.
 *
 * Colors are the validated dataviz reference palette (categorical slots 1–2),
 * stepped separately for light and dark surfaces via CSS custom properties.
 * Marks are thin with 4px-rounded data ends; grid/axes stay recessive; every
 * mark has a hover tooltip; text wears the app's ink tokens, never series hues.
 */

import * as React from "react";

import { cn } from "@/lib/utils";

// Categorical slots 1 (blue) + 2 (orange), light/dark steps. Validated with
// the dataviz palette validator (all checks pass in both modes).
const PALETTE_VARS =
  "[--s1:#2a78d6] [--s2:#eb6834] dark:[--s1:#3987e5] dark:[--s2:#d95926]";

type Datum = { label: string; value: number };

function niceMax(value: number): number {
  if (value <= 5) return 5;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const scaled = value / magnitude;
  const step = scaled <= 2 ? 2 : scaled <= 5 ? 5 : 10;
  return step * magnitude;
}

/** Bar anchored to the baseline with a 4px-rounded top end. */
function barPath(x: number, y: number, w: number, h: number): string {
  const r = Math.min(4, w / 2, h);
  return [
    `M${x},${y + h}`,
    `L${x},${y + r}`,
    `Q${x},${y} ${x + r},${y}`,
    `L${x + w - r},${y}`,
    `Q${x + w},${y} ${x + w},${y + r}`,
    `L${x + w},${y + h}`,
    "Z",
  ].join(" ");
}

/** Horizontal bar anchored to the left axis with a 4px-rounded right end. */
function hBarPath(x: number, y: number, w: number, h: number): string {
  const r = Math.min(4, h / 2, w);
  return [
    `M${x},${y}`,
    `L${x + w - r},${y}`,
    `Q${x + w},${y} ${x + w},${y + r}`,
    `L${x + w},${y + h - r}`,
    `Q${x + w},${y + h} ${x + w - r},${y + h}`,
    `L${x},${y + h}`,
    "Z",
  ].join(" ");
}

function ChartTooltip({
  tip,
}: {
  tip: { x: number; y: number; lines: string[] } | null;
}) {
  if (!tip) return null;
  return (
    <div
      className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-md border bg-popover px-2.5 py-1.5 text-xs text-popover-foreground shadow-md"
      style={{ left: tip.x, top: tip.y - 8 }}
    >
      {tip.lines.map((line) => (
        <div key={line}>{line}</div>
      ))}
    </div>
  );
}

function useTooltip() {
  const [tip, setTip] = React.useState<{
    x: number;
    y: number;
    lines: string[];
  } | null>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);

  const show = (event: React.MouseEvent, lines: string[]) => {
    const bounds = containerRef.current?.getBoundingClientRect();
    if (!bounds) return;
    setTip({
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top,
      lines,
    });
  };
  return { tip, show, hide: () => setTip(null), containerRef };
}

const W = 560;

/** Vertical single-series bar chart. One hue — identity lives on the x axis. */
export function BarChart({
  data,
  className,
}: {
  data: Datum[];
  className?: string;
}) {
  const { tip, show, hide, containerRef } = useTooltip();
  const height = 220;
  const pad = { top: 12, right: 8, bottom: 28, left: 34 };
  const plotW = W - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const max = niceMax(Math.max(1, ...data.map((d) => d.value)));
  const slot = plotW / Math.max(1, data.length);
  const barW = Math.min(48, slot * 0.55);
  const ticks = [0, max / 2, max];

  return (
    <div ref={containerRef} className={cn("relative", PALETTE_VARS, className)}>
      <svg
        viewBox={`0 0 ${W} ${height}`}
        className="w-full"
        role="img"
        aria-label="Bar chart"
      >
        {ticks.map((t) => {
          const y = pad.top + plotH - (t / max) * plotH;
          return (
            <g key={t}>
              <line
                x1={pad.left}
                x2={W - pad.right}
                y1={y}
                y2={y}
                className="stroke-border"
                strokeWidth={1}
              />
              <text
                x={pad.left - 6}
                y={y + 3}
                textAnchor="end"
                className="fill-muted-foreground text-[10px] [font-variant-numeric:tabular-nums]"
              >
                {t}
              </text>
            </g>
          );
        })}
        {data.map((d, i) => {
          const h = (d.value / max) * plotH;
          const x = pad.left + i * slot + (slot - barW) / 2;
          const y = pad.top + plotH - h;
          return (
            <g key={d.label}>
              {d.value > 0 && (
                <path
                  d={barPath(x, y, barW, h)}
                  fill="var(--s1)"
                  onMouseMove={(e) => show(e, [`${d.label}: ${d.value}`])}
                  onMouseLeave={hide}
                />
              )}
              <text
                x={x + barW / 2}
                y={height - 10}
                textAnchor="middle"
                className="fill-muted-foreground text-[10px]"
              >
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
      <ChartTooltip tip={tip} />
    </div>
  );
}

/** Two-series grouped bars over time, with a legend (identity ≠ color-alone). */
export function GroupedBarChart({
  data,
  seriesLabels,
  className,
}: {
  data: { label: string; a: number; b: number }[];
  seriesLabels: [string, string];
  className?: string;
}) {
  const { tip, show, hide, containerRef } = useTooltip();
  const height = 220;
  const pad = { top: 12, right: 8, bottom: 28, left: 34 };
  const plotW = W - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;
  const max = niceMax(Math.max(1, ...data.flatMap((d) => [d.a, d.b])));
  const slot = plotW / Math.max(1, data.length);
  const barW = Math.min(20, slot * 0.28);
  const ticks = [0, max / 2, max];

  return (
    <div ref={containerRef} className={cn("relative", PALETTE_VARS, className)}>
      <div className="mb-2 flex items-center gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-[3px] bg-(--s1)" />
          {seriesLabels[0]}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-[3px] bg-(--s2)" />
          {seriesLabels[1]}
        </span>
      </div>
      <svg
        viewBox={`0 0 ${W} ${height}`}
        className="w-full"
        role="img"
        aria-label={`${seriesLabels[0]} vs ${seriesLabels[1]}`}
      >
        {ticks.map((t) => {
          const y = pad.top + plotH - (t / max) * plotH;
          return (
            <g key={t}>
              <line
                x1={pad.left}
                x2={W - pad.right}
                y1={y}
                y2={y}
                className="stroke-border"
                strokeWidth={1}
              />
              <text
                x={pad.left - 6}
                y={y + 3}
                textAnchor="end"
                className="fill-muted-foreground text-[10px] [font-variant-numeric:tabular-nums]"
              >
                {t}
              </text>
            </g>
          );
        })}
        {data.map((d, i) => {
          const hA = (d.a / max) * plotH;
          const hB = (d.b / max) * plotH;
          const center = pad.left + i * slot + slot / 2;
          // 2px surface gap between the paired bars.
          const xA = center - barW - 1;
          const xB = center + 1;
          const lines = [
            d.label,
            `${seriesLabels[0]}: ${d.a}`,
            `${seriesLabels[1]}: ${d.b}`,
          ];
          return (
            <g key={d.label} onMouseLeave={hide}>
              {d.a > 0 && (
                <path
                  d={barPath(xA, pad.top + plotH - hA, barW, hA)}
                  fill="var(--s1)"
                  onMouseMove={(e) => show(e, lines)}
                />
              )}
              {d.b > 0 && (
                <path
                  d={barPath(xB, pad.top + plotH - hB, barW, hB)}
                  fill="var(--s2)"
                  onMouseMove={(e) => show(e, lines)}
                />
              )}
              <rect
                x={pad.left + i * slot}
                y={pad.top}
                width={slot}
                height={plotH}
                fill="transparent"
                onMouseMove={(e) => show(e, lines)}
              />
              <text
                x={center}
                y={height - 10}
                textAnchor="middle"
                className="fill-muted-foreground text-[10px]"
              >
                {d.label}
              </text>
            </g>
          );
        })}
      </svg>
      <ChartTooltip tip={tip} />
    </div>
  );
}

/** Horizontal single-series bars — best for people/name labels. */
export function HBarChart({
  data,
  className,
}: {
  data: Datum[];
  className?: string;
}) {
  const { tip, show, hide, containerRef } = useTooltip();
  const rowH = 30;
  const pad = { top: 4, right: 36, bottom: 4, left: 120 };
  const height = pad.top + pad.bottom + rowH * Math.max(1, data.length);
  const plotW = W - pad.left - pad.right;
  const max = niceMax(Math.max(1, ...data.map((d) => d.value)));

  return (
    <div ref={containerRef} className={cn("relative", PALETTE_VARS, className)}>
      <svg
        viewBox={`0 0 ${W} ${height}`}
        className="w-full"
        role="img"
        aria-label="Horizontal bar chart"
      >
        {data.map((d, i) => {
          const w = (d.value / max) * plotW;
          const y = pad.top + i * rowH + (rowH - 14) / 2;
          return (
            <g key={d.label}>
              <text
                x={pad.left - 8}
                y={y + 11}
                textAnchor="end"
                className="fill-muted-foreground text-[11px]"
              >
                {d.label.length > 18 ? `${d.label.slice(0, 17)}…` : d.label}
              </text>
              {d.value > 0 && (
                <path
                  d={hBarPath(pad.left, y, Math.max(w, 4), 14)}
                  fill="var(--s1)"
                  onMouseMove={(e) => show(e, [`${d.label}: ${d.value}`])}
                  onMouseLeave={hide}
                />
              )}
              <text
                x={pad.left + Math.max(w, 4) + 6}
                y={y + 11}
                className="fill-muted-foreground text-[10px] [font-variant-numeric:tabular-nums]"
              >
                {d.value}
              </text>
            </g>
          );
        })}
      </svg>
      <ChartTooltip tip={tip} />
    </div>
  );
}

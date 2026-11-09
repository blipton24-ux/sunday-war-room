"use client";

import { useEffect, useState } from "react";

import { winTone } from "@/lib/insights";

const TONE = { good: "var(--good)", ok: "var(--ok)", bad: "var(--bad)" } as const;

/** The win-chance ring (ADR-032): fills to the value, colored green / yellow / red. */
export function Ring({
  value,
  size = 76,
  stroke = 7,
  label = "Win chance",
  tone,
}: {
  value: number;
  size?: number;
  stroke?: number;
  label?: string;
  tone?: keyof typeof TONE;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [shown, setShown] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(value));
    return () => cancelAnimationFrame(id);
  }, [value]);
  const color = TONE[tone ?? winTone(value)];
  return (
    <span className="inline-flex shrink-0 flex-col items-center gap-1.5">
      <span className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90" aria-hidden>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} stroke="var(--high)" />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            strokeWidth={stroke}
            strokeLinecap="round"
            stroke={color}
            strokeDasharray={c}
            strokeDashoffset={c * (1 - shown)}
            style={{ transition: "stroke-dashoffset 1s ease-out" }}
          />
        </svg>
        <span
          className="stat absolute inset-0 grid place-items-center text-ink"
          style={{ fontSize: Math.max(11, Math.round(size * 0.26)) }}
        >
          {Math.round(value * 100)}%
        </span>
      </span>
      {label && <span className="text-[0.72rem] font-medium text-ink-lo">{label}</span>}
    </span>
  );
}

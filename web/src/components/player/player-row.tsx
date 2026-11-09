"use client";

import Image from "next/image";
import { useState } from "react";

import { Chip } from "@/components/ui/primitives";
import type { Schemas } from "@/lib/api/client";
import { usePlayerProjection } from "@/lib/api/queries";
import { cn } from "@/lib/cn";
import { f1, signed } from "@/lib/format";
import { headlinePoints, rangeStyle, vibe } from "@/lib/insights";
import { positionLabel, positionText } from "@/lib/positions";
import { espnLogo } from "@/lib/images";

import { PlayerAvatar } from "./avatar";
import { RangeBar } from "./range-bar";

type Line = Schemas["PlayerLine"];

const FACTOR_LABEL: Record<string, string> = {
  baseline: "Recent form",
  opponent: "Opponent",
  role: "Role",
  depth: "Depth chart",
  injury: "Injury",
  bye: "Bye",
};

function factorValue(f: Schemas["Factor"]): string {
  return f.name === "baseline" ? f1(f.value) : `×${f.value.toFixed(2)}`;
}

/** A tappable player row; expanding it shows the range, the reasons, and recent games. */
export function PlayerRow({
  player,
  leagueId,
  week,
  dim,
  recommended,
  index = 0,
}: {
  player: Line;
  leagueId: number;
  week: number;
  dim?: boolean;
  recommended?: boolean;
  index?: number;
}) {
  const [open, setOpen] = useState(false);
  const detail = usePlayerProjection(player.player_id, leagueId, week, open);
  const head = headlinePoints(player);
  const v = vibe(player);
  const injury = player.injury_status;
  const pr = player.projection;

  return (
    <div
      className={cn(
        "animate-fade-up relative overflow-hidden rounded-[1.25rem] bg-raised transition-colors hover:bg-overlay",
        open && "bg-overlay",
        dim && !open && "opacity-75",
      )}
      style={{ animationDelay: `${Math.min(index, 12) * 35}ms` }}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex min-h-16 w-full items-center gap-3 py-2.5 pl-2.5 pr-3.5 text-left"
      >
        <PlayerAvatar
          name={player.name}
          team={player.nfl_team}
          position={player.position}
          imageUrl={player.headshot_url}
          slot={player.slot}
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[0.95rem] font-semibold">{player.name}</span>
          <span className="mt-1 flex items-center gap-1.5 text-[0.72rem]">
            {player.nfl_team && player.position !== "DEF" && (
              <Image src={espnLogo(player.nfl_team)} alt="" width={14} height={14} className="size-3.5 object-contain" />
            )}
            <b className={positionText(player.position)}>{positionLabel(player.position)}</b>
            <span className="truncate text-ink-faint">
              {player.nfl_team} {player.opponent ?? "BYE"}
            </span>
            {injury && <Tag tone="warn">{injury.slice(0, 1).toUpperCase()}</Tag>}
            {player.game_status === "bye" && <Tag tone="neutral">BYE</Tag>}
            {recommended && <Tag tone="good">Start</Tag>}
          </span>
        </span>
        <span className="flex shrink-0 flex-col items-end">
          <span className="flex items-center gap-1.5">
            {v === "boom" && <Tag tone="good">🔥 Boom</Tag>}
            {player.game_status === "in_progress" && <Chip tone="live">Live</Chip>}
            <span className="stat text-[1.4rem]">{head.main}</span>
          </span>
          <small className="nums mt-1 text-[0.68rem] text-ink-faint">{head.sub}</small>
        </span>
      </button>

      {open && (
        <div className="px-3 pb-3.5">
          <div className="flex items-center gap-1.5 border-t border-line pt-3">
            <span className="text-xs font-semibold text-ink-mid">This week</span>
            {player.game_status === "bye" ? (
              <Tag tone="neutral">On bye</Tag>
            ) : v === "boom" ? (
              <Tag tone="good">🔥 Boom</Tag>
            ) : v === "bust" ? (
              <Tag tone="bad">Bust</Tag>
            ) : pr ? (
              <Tag tone="neutral">{rangeStyle(pr) === "volatile" ? "🎢 Boom or bust" : "🧱 Steady"}</Tag>
            ) : null}
          </div>

          {pr && player.game_status !== "bye" && (
            <div className="mt-1.5">
              <RangeBar p10={pr.p10} points={pr.points} p90={pr.p90} actual={player.actual_points} />
            </div>
          )}

          {detail.isLoading && <p className="mt-3 text-xs text-ink-lo">Loading the details…</p>}
          {detail.data && (
            <>
              {detail.data.factors.length > 0 && (
                <div className="mt-3">
                  <p className="mb-1.5 text-[0.7rem] font-semibold text-sea">Why this number</p>
                  <div className="flex flex-wrap gap-1.5">
                    {detail.data.factors.map((f) => (
                      <span
                        key={f.name}
                        title={f.note}
                        className="rounded-full bg-high px-2.5 py-1 text-[0.7rem] font-semibold text-ink-mid"
                      >
                        {FACTOR_LABEL[f.name] ?? f.name} <b className="nums text-ink">{factorValue(f)}</b>
                        {f.name !== "baseline" && f.effect !== 0 && (
                          <span className={cn("nums ml-1", f.effect > 0 ? "text-good" : "text-bad")}>
                            {signed(f.effect)}
                          </span>
                        )}
                      </span>
                    ))}
                  </div>
                  <ul className="mt-2 space-y-1 text-[0.72rem] text-ink-lo">
                    {detail.data.factors.map((f) => (
                      <li key={f.name}>{f.note}</li>
                    ))}
                  </ul>
                </div>
              )}
              {detail.data.recent_games.length > 0 && (
                <div className="mt-3">
                  <p className="mb-1.5 text-[0.7rem] font-semibold text-sea">Recent games</p>
                  <div className="flex gap-1.5">
                    {detail.data.recent_games.map((g) => (
                      <span key={g.week} className="rounded-xl bg-high px-2.5 py-1.5 text-center">
                        <span className="stat block text-sm">{f1(g.points)}</span>
                        <span className="text-[0.62rem] text-ink-lo">
                          Wk {g.week} {g.opponent ?? ""}
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
          {pr && (
            <p className="mt-3 inline-flex items-center gap-1.5 text-[0.72rem] text-ink-lo">
              <i className={cn("size-2 rounded-full", pr.frozen ? "bg-sea" : "bg-good")} />
              {pr.frozen ? "Frozen at kickoff" : "Updates until kickoff"} · model {pr.model_version}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function Tag({ tone, children }: { tone: "warn" | "neutral" | "good" | "bad"; children: React.ReactNode }) {
  const cls = {
    warn: "bg-warn/15 text-warn",
    neutral: "bg-high text-ink-lo",
    good: "bg-good/15 text-good",
    bad: "bg-bad/15 text-bad",
  }[tone];
  return <span className={cn("rounded-full px-1.5 text-[0.62rem] font-bold leading-4", cls)}>{children}</span>;
}

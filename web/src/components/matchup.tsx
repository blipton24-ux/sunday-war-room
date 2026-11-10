"use client";

import { Chip } from "@/components/ui/primitives";
import { Ring } from "@/components/ui/ring";
import type { Schemas } from "@/lib/api/client";
import { cn } from "@/lib/cn";
import { f1, pct } from "@/lib/format";
import { bestPoints, matchupStatus } from "@/lib/insights";
import { slotBg, slotLabel } from "@/lib/positions";

import { PlayerAvatar, TeamBadge } from "./player/avatar";

type Matchup = Schemas["MatchupOut"];
type Side = Schemas["TeamSide"];
type Line = Schemas["PlayerLine"];

export const MY_COLOR = "#2F6BDB";
export const OPP_COLOR = "#C14E69"; // darkened a little so white initials pass contrast

function gameState(m: Matchup): "live" | "final" | null {
  const all = [...m.me.starters, ...(m.opponent?.starters ?? [])].filter((p) => p.game_status !== "bye");
  if (all.some((p) => p.game_status === "in_progress")) return "live";
  if (all.length > 0 && all.every((p) => p.game_status === "final")) return "final";
  return null;
}

function StateChip({ state }: { state: "live" | "final" | null }) {
  if (state === "live") return <Chip tone="live">Live</Chip>;
  if (state === "final") return <Chip tone="final">Final</Chip>;
  return null;
}

function Who({ side, color, right }: { side: Side; color: string; right?: boolean }) {
  return (
    <div className={cn("flex w-full min-w-0 items-center gap-2", right && "flex-row-reverse")}>
      <TeamBadge name={side.name} avatarUrl={side.avatar_url} color={color} />
      <div className="min-w-0">
        <div className="truncate text-sm font-bold">{side.name}</div>
        <div className="nums text-xs text-ink-mid">{side.record}</div>
      </div>
    </div>
  );
}

function Sides({ m, showProjection }: { m: Matchup; showProjection?: boolean }) {
  const opp = m.opponent;
  const myScore = m.me.score ?? 0;
  const oppScore = opp?.score ?? 0;
  const leading = myScore >= oppScore;
  return (
    <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-end gap-3">
      <div className="flex min-w-0 flex-col gap-2.5">
        <Who side={m.me} color={MY_COLOR} />
        <span className={cn("stat text-[2.6rem] sm:text-[3.75rem]", !leading && "text-ink-faint")}>
          {f1(myScore)}
        </span>
        {showProjection && <span className="nums text-xs text-ink-lo">proj {f1(m.me.projected_total)}</span>}
      </div>
      <span className="pb-3 font-display text-sm font-black italic text-ink-faint">VS</span>
      {opp ? (
        <div className="flex min-w-0 flex-col items-end gap-2.5 text-right">
          <Who side={opp} color={OPP_COLOR} right />
          <span className={cn("stat text-[2.6rem] sm:text-[3.75rem]", leading && "text-ink-faint")}>
            {f1(oppScore)}
          </span>
          {showProjection && <span className="nums text-xs text-ink-lo">proj {f1(opp.projected_total)}</span>}
        </div>
      ) : (
        <div className="self-center text-right text-sm text-ink-lo">No opponent this week</div>
      )}
    </div>
  );
}

/** Score header used on Home and Lineup (mockup "hero"). */
export function ScoreHero({ matchup: m }: { matchup: Matchup }) {
  const status = m.outlook ? matchupStatus(m.outlook.win_probability) : null;
  const diff = (m.me.score ?? 0) - (m.opponent?.score ?? 0);
  const scored = (m.me.score ?? 0) > 0 || (m.opponent?.score ?? 0) > 0;
  return (
    <div className="animate-fade-up relative overflow-hidden rounded-[1.5rem] bg-raised px-[18px] pb-[18px] pt-4 shadow-card">
      <span className="absolute inset-y-0 left-0 w-1 bg-accent" />
      <div className="flex items-center justify-between text-xs font-semibold text-ink-mid">
        <span className="flex items-center gap-2">
          Week {m.week} <StateChip state={gameState(m)} />
        </span>
        <Chip tone="dim" className="nums">
          Projected final {f1(m.me.projected_total)}
        </Chip>
      </div>
      <Sides m={m} />
      {status && (
        <div className="mt-3.5 flex justify-center">
          <Chip tone={status.tone === "ok" ? "warn" : status.tone} className="px-3 py-1 text-[0.8rem]">
            {status.emoji} {status.label}
            {scored && diff !== 0
              ? `: ${diff > 0 ? "up" : "down"} ${f1(Math.abs(diff))}`
              : ` · ${pct(m.outlook!.win_probability)} to win`}
          </Chip>
        </div>
      )}
    </div>
  );
}

/** Scoreboard card with the "Projected to win" panel (Matchup screen). */
export function MatchupBoard({ matchup: m }: { matchup: Matchup }) {
  const opp = m.opponent;
  const my = m.me.score ?? 0;
  const their = opp?.score ?? 0;
  const useProjected = my + their === 0;
  const a = useProjected ? m.me.projected_total : my;
  const b = useProjected ? (opp?.projected_total ?? 0) : their;
  const share = a + b > 0 ? a / (a + b) : 0.5;
  const o = m.outlook;
  const iWin = o ? o.win_probability >= 0.5 : true;
  return (
    <div className="animate-fade-up overflow-hidden rounded-[1.5rem] bg-raised shadow-card">
      <div className="flex items-center justify-center gap-2 px-3 pt-3 text-xs font-medium text-ink-lo">
        <span>Week {m.week}</span>
        <StateChip state={gameState(m)} />
      </div>
      <div className="px-[18px] pb-[18px] pt-3">
        <Sides m={m} showProjection />
        {opp && (
          <div className="mt-[18px] flex h-2 gap-0.5 overflow-hidden rounded-full" aria-hidden>
            <div style={{ width: `${share * 100}%`, background: MY_COLOR }} className="transition-[width] duration-700" />
            <div className="flex-1 opacity-35" style={{ background: OPP_COLOR }} />
          </div>
        )}
        {opp && gameState(m) === "final" ? (
          <div className="mt-4 rounded-[1.1rem] bg-overlay px-3.5 py-3">
            <div className="text-[0.72rem] font-semibold text-sea">Final</div>
            <div className="mt-0.5 truncate font-display text-lg font-extrabold [font-stretch:112%]">
              {my === their ? "Tied" : `${my > their ? m.me.name : opp.name} won`}
            </div>
            <div className="nums mt-0.5 text-xs text-ink-lo">
              {f1(my)} – {f1(their)} · margin {f1(Math.abs(my - their))}
            </div>
          </div>
        ) : (
          o &&
          opp && (
            <div className="mt-4 flex items-center gap-3.5 rounded-[1.1rem] bg-overlay px-3.5 py-3">
              <Ring value={o.win_probability} size={58} stroke={6} label="" />
              <div className="min-w-0">
                <div className="text-[0.72rem] font-semibold text-sea">Projected to win</div>
                <div className="mt-0.5 truncate font-display text-lg font-extrabold [font-stretch:112%]">
                  {iWin ? m.me.name : opp.name}
                </div>
                <div className="nums mt-0.5 text-xs text-ink-lo">
                  {f1(o.my_median)} – {f1(o.opponent_median)} projected final · {pct(o.win_probability)}{" "}
                  win chance
                </div>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}

function Cell({ p, lead, right }: { p: Line | undefined; lead: boolean; right?: boolean }) {
  if (!p) return <div className="rounded-[1.1rem] bg-raised/50" />;
  const final = p.actual_points != null;
  const live = p.game_status === "in_progress" && p.live_points != null;
  const value = p.game_status === "bye" ? "--" : live ? f1(p.live_points) : f1(bestPoints(p));
  const sub =
    p.game_status === "bye"
      ? "bye"
      : live
        ? `→ ${f1(bestPoints(p))}`
        : final
          ? `proj ${f1(p.projection?.points)}`
          : "proj";
  return (
    <div
      className={cn(
        "flex min-w-0 items-center gap-2.5 rounded-[1.1rem] bg-raised px-2.5 py-2",
        right && "flex-row-reverse text-right",
      )}
    >
      <span className="hidden min-[421px]:inline-block">
        <PlayerAvatar name={p.name} team={p.nfl_team} position={p.position} imageUrl={p.headshot_url} size={34} mirror={right} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[0.82rem] font-semibold">{p.name}</div>
        <div className="nums mt-0.5 truncate text-[0.66rem] text-ink-faint">
          {p.nfl_team} {p.opponent ?? "BYE"}
          {p.game_status === "in_progress" && p.game_detail && <> · {p.game_detail}</>}
          {p.has_ball && <span aria-label="has the ball"> ●</span>}
        </div>
      </div>
      <div className={right ? "text-left" : "text-right"}>
        <div className={cn("stat text-[1.15rem]", lead && "text-accent")}>{value}</div>
        <div className="nums mt-0.5 text-[0.66rem] text-ink-faint">{sub}</div>
      </div>
    </div>
  );
}

/** Starters side by side by slot; the leader's number in bronze. */
export function HeadToHead({ matchup: m }: { matchup: Matchup }) {
  const mine = m.me.starters;
  const theirs = m.opponent?.starters ?? [];
  const rows = Math.max(mine.length, theirs.length);
  return (
    <div className="flex flex-col gap-1.5">
      {Array.from({ length: rows }, (_, i) => {
        const a = mine[i];
        const b = theirs[i];
        const slot = a?.slot ?? b?.slot ?? "";
        const pa = a ? bestPoints(a) : -Infinity;
        const pb = b ? bestPoints(b) : -Infinity;
        return (
          <div
            key={i}
            className="animate-fade-up grid grid-cols-[1fr_40px_1fr] items-stretch gap-1.5"
            style={{ animationDelay: `${i * 30}ms` }}
          >
            <Cell p={a} lead={pa > pb} />
            <span className="grid place-items-center">
              <span className={cn("rounded-md px-1.5 py-0.5 text-[0.6rem] font-black text-[#0b1016]", slotBg(slot))}>
                {slotLabel(slot)}
              </span>
            </span>
            <Cell p={b} lead={pb > pa} right />
          </div>
        );
      })}
    </div>
  );
}

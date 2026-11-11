"use client";

import Image from "next/image";

import { Card, Section } from "@/components/ui/primitives";
import { Ring } from "@/components/ui/ring";
import type { Schemas } from "@/lib/api/client";
import { f1, initials, lastName, pct, signed } from "@/lib/format";
import { bestPoints, topPerformers, vibe } from "@/lib/insights";
import { slotBg, slotLabel } from "@/lib/positions";
import { teamColor } from "@/lib/teams";

import { PlayerAvatar } from "./player/avatar";

type Lineup = Schemas["LineupOut"];
type Line = Schemas["PlayerLine"];

/** "Lineup check": win-chance ring and the swaps to make (ADR-032). */
export function LineupCheck({ lineup }: { lineup: Lineup }) {
  const now = lineup.win_probability_current;
  const best = lineup.win_probability_optimal;
  const n = lineup.swaps.length;
  return (
    <Card glow className="animate-fade-up flex items-start gap-4">
      {now != null ? (
        <Ring value={now} />
      ) : (
        <span className="grid size-[76px] shrink-0 place-items-center rounded-full bg-high text-xs text-ink-lo">
          no opp.
        </span>
      )}
      <div className="min-w-0 flex-1 pt-1">
        <div className="font-bold">
          {n === 0 ? "Your lineup is already the best one ✓" : `${n} swap${n > 1 ? "s" : ""} to make`}
        </div>
        {lineup.swaps.map((s) => (
          <div
            key={`${s.player_in.player_id}-${s.player_out?.player_id ?? "empty"}`}
            className="mt-2 flex items-center gap-2.5 rounded-[14px] bg-overlay px-2.5 py-2 text-sm"
          >
            <PlayerAvatar
              name={s.player_in.name}
              team={s.player_in.nfl_team}
              position={s.player_in.position}
              imageUrl={s.player_in.headshot_url}
              size={30}
            />
            <span className="font-extrabold text-good">▲</span>
            <span className="truncate font-bold">{lastName(s.player_in.name)}</span>
            {s.player_out && (
              <span className="truncate text-ink-lo line-through decoration-wine">
                {lastName(s.player_out.name)}
              </span>
            )}
            <span className="nums ml-auto font-bold text-accent">{signed(s.gain)}</span>
          </div>
        ))}
        <p className="mt-2 text-xs text-ink-lo">
          {n > 0 && now != null && best != null
            ? `Win chance ${pct(now)} → ${pct(best)}. Make the change in your fantasy app.`
            : n > 0
              ? "Make the change in your fantasy app."
              : `Projected ${f1(lineup.current_points)} points from your starters.`}
        </p>
      </div>
    </Card>
  );
}

function Poster({ p, rank }: { p: Line; rank: number }) {
  const color = teamColor(p.nfl_team);
  const v = vibe(p);
  return (
    <div
      className="animate-fade-up relative h-[184px] shrink-0 basis-[136px] snap-start overflow-hidden rounded-[1.25rem] bg-raised shadow-card"
      style={{ animationDelay: `${rank * 50}ms` }}
    >
      <div className="absolute inset-x-0 top-0 h-[118px] overflow-hidden" style={{ background: color }}>
        {p.headshot_url ? (
          <Image
            src={p.headshot_url}
            alt=""
            width={240}
            height={175}
            sizes="136px"
            className={
              p.position === "DEF"
                ? "absolute inset-[18px] h-[calc(100%-36px)] w-[calc(100%-36px)] object-contain"
                : "absolute bottom-0 left-1/2 h-full w-auto max-w-none -translate-x-1/2"
            }
          />
        ) : (
          <span className="absolute inset-0 grid place-items-center font-display text-3xl font-extrabold text-white">
            {initials(p.name)}
          </span>
        )}
      </div>
      <span className="absolute left-2.5 top-1.5 font-display text-2xl font-black text-white">{rank}</span>
      <span className={`absolute right-2.5 top-2.5 rounded-md px-1.5 text-[0.6rem] font-black leading-[1.15rem] text-[#0b1016] ${slotBg(p.slot)}`}>
        {slotLabel(p.slot)}
      </span>
      <div className="absolute inset-x-0 bottom-0 bg-raised px-2.5 pb-2.5 pt-2">
        <div className="truncate text-[0.8rem] font-bold">{p.name}</div>
        <div className="mt-0.5 flex items-baseline gap-1.5">
          <span className="stat text-[1.4rem]">{f1(bestPoints(p))}</span>
          <small className="text-[0.68rem] text-ink-lo">
            {v === "boom" ? "🔥 Boom" : p.actual_points != null ? "final" : "proj"}
          </small>
        </div>
      </div>
    </div>
  );
}

/** "Top performers" shelf: the best of your starters this week. */
export function TopPerformers({ starters }: { starters: readonly Line[] }) {
  const top = topPerformers(starters);
  if (top.length === 0) return null;
  return (
    <Section title="Top performers">
      <div className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-1 [scrollbar-width:none]">
        {top.map((p, i) => (
          <Poster key={p.player_id} p={p} rank={i + 1} />
        ))}
      </div>
    </Section>
  );
}

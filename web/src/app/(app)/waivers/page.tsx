"use client";

import { TrendingUp } from "lucide-react";
import { useState } from "react";

import { useLeague } from "@/components/league-context";
import { PlayerAvatar } from "@/components/player/avatar";
import { Gate, TitleRow } from "@/components/screen";
import { Card, Chip, EmptyState, Section } from "@/components/ui/primitives";
import type { Schemas } from "@/lib/api/client";
import { useWaivers, type WaiverHorizon } from "@/lib/api/queries";
import { cn } from "@/lib/cn";
import { f1 } from "@/lib/format";
import { positionLabel } from "@/lib/positions";

type Waivers = Schemas["WaiversOut"];
type Row = Schemas["WaiverPlayer"];

export default function WaiversPage() {
  const { leagueId } = useLeague();
  const [horizon, setHorizon] = useState<WaiverHorizon>("ros");
  const waivers = useWaivers(leagueId, horizon);

  return (
    <Gate query={waivers}>
      {(w) => (
        <>
          <TitleRow title="Waivers" note={horizonNote(w)} />
          <HorizonToggle value={horizon} onChange={setHorizon} />
          <RulesCard w={w} />
          <WaiverList w={w} />
        </>
      )}
    </Gate>
  );
}

function horizonNote(w: Waivers): string {
  if (w.horizon === "week") return `week ${w.week} only`;
  const weeks = w.horizon_weeks;
  if (weeks.length === 0) return "season over";
  const span = `weeks ${weeks[0]}–${weeks[weeks.length - 1]}`;
  return w.playoff_weeks.length ? `${span}, playoff weeks count 1.5×` : span;
}

function HorizonToggle({ value, onChange }: { value: WaiverHorizon; onChange: (h: WaiverHorizon) => void }) {
  const options: [WaiverHorizon, string][] = [
    ["ros", "Rest of season"],
    ["week", "This week"],
  ];
  return (
    <div role="group" aria-label="Value over" className="flex rounded-full bg-raised p-1">
      {options.map(([key, label]) => (
        <button
          key={key}
          type="button"
          aria-pressed={value === key}
          onClick={() => onChange(key)}
          className={cn(
            "min-h-11 flex-1 rounded-full px-3 text-sm font-bold text-ink-mid transition-colors",
            value === key && "bg-overlay text-ink",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

function RulesCard({ w }: { w: Waivers }) {
  let text: React.ReactNode;
  if (w.waiver_kind === "faab") {
    text = (
      <>
        <b className="text-ink">FAAB:</b> ${w.faab_remaining ?? 0} of ${w.faab_budget ?? 0} left. Bid ranges are a
        guide from how much each player adds to your lineup.
      </>
    );
  } else if (w.waiver_kind === "none") {
    text = <>This league has no waivers: every free agent can be added right away.</>;
  } else {
    const order = w.waiver_kind === "reverse_standings" ? "reverse standings" : "rolling priority";
    text = (
      <>
        <b className="text-ink">Waiver priority ({order}):</b>{" "}
        {w.my_waiver_position ? <>you claim #{w.my_waiver_position}.</> : null}
      </>
    );
  }
  return (
    <Card>
      <p className="text-sm text-ink-mid">
        {text}
        {w.clear_days > 0 && (
          <>
            {" "}
            Dropped players stay on waivers for {w.clear_days} day{w.clear_days === 1 ? "" : "s"}.
          </>
        )}{" "}
        Make the move in your fantasy app.
      </p>
    </Card>
  );
}

function WaiverList({ w }: { w: Waivers }) {
  if (!w.ready) {
    return (
      <EmptyState icon={TrendingUp} title="Projecting free agents">
        Free agents are projected after each sync. Refresh the league, or check back in a minute.
      </EmptyState>
    );
  }
  const helpful = w.players.filter((p) => p.gain > 0);
  if (helpful.length === 0) {
    return (
      <EmptyState icon={TrendingUp} title="Your lineup is set">
        No free agent would improve your best lineup {w.horizon === "week" ? "this week" : "for the rest of the season"}.
      </EmptyState>
    );
  }
  return (
    <Section title="Best adds for your lineup">
      <ol className="flex flex-col gap-1.5">
        {helpful.map((p, i) => (
          <WaiverRow key={p.player.player_id} row={p} rank={i + 1} />
        ))}
      </ol>
    </Section>
  );
}

function untilLabel(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" });
}

function WaiverRow({ row, rank }: { row: Row; rank: number }) {
  const p = row.player;
  return (
    <li className="animate-fade-up rounded-[1.25rem] bg-raised py-2.5 pl-2.5 pr-3.5" style={{ animationDelay: `${Math.min(rank, 12) * 35}ms` }}>
      <div className="flex items-center gap-3">
        <PlayerAvatar name={p.name} team={p.nfl_team} position={p.position} imageUrl={p.headshot_url} />
        <div className="min-w-0 flex-1">
          <div className="truncate text-[0.95rem] font-semibold">{p.name}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[0.72rem] text-ink-lo">
            <span>
              {positionLabel(p.position)} · {p.nfl_team ?? "FA"} · {f1(row.points_per_week)} pts/wk
            </span>
            {p.injury_status && <Chip tone="warn">{p.injury_status}</Chip>}
          </div>
        </div>
        <div className="text-right">
          <div className="nums font-display text-lg font-extrabold text-good">+{f1(row.gain_per_week)}</div>
          <div className="text-[0.66rem] text-ink-lo">pts/wk to your lineup</div>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-1.5 pl-[3.6rem]">
        {row.status === "waivers" && row.on_waivers_until ? (
          <Chip tone="warn">On waivers until about {untilLabel(row.on_waivers_until)}</Chip>
        ) : (
          <Chip tone="good">Free agent · add now</Chip>
        )}
        {row.bid_low != null && row.bid_high != null && (
          <Chip tone="accent">
            Bid ${row.bid_low}
            {row.bid_high !== row.bid_low ? `–${row.bid_high}` : ""}
          </Chip>
        )}
        {row.drop && <Chip tone="neutral">Drop {row.drop.name}</Chip>}
      </div>
    </li>
  );
}

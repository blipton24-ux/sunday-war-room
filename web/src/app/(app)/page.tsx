"use client";

import Link from "next/link";

import { useLeague } from "@/components/league-context";
import { ScoreHero } from "@/components/matchup";
import { PlayerAvatar } from "@/components/player/avatar";
import { Gate, TitleRow } from "@/components/screen";
import { Card, Section } from "@/components/ui/primitives";
import { Ring } from "@/components/ui/ring";
import type { Schemas } from "@/lib/api/client";
import { useAccuracy, useLineup, useMatchup } from "@/lib/api/queries";
import { cn } from "@/lib/cn";
import { f1, kickoffLabel, pct } from "@/lib/format";
import { headsUp, stillToPlay } from "@/lib/insights";

function statusLine(m: Schemas["MatchupOut"]): string {
  const left = stillToPlay(m.me.starters);
  if (left === 0) return "All your starters have played";
  const next = m.me.starters
    .filter((p) => p.game_status === "upcoming" && p.kickoff_at)
    .map((p) => p.kickoff_at!)
    .sort()[0];
  return `${left} starter${left > 1 ? "s" : ""} still to play${next ? ` · next ${kickoffLabel(next)}` : ""}`;
}

export default function HomePage() {
  const { leagueId, week } = useLeague();
  const matchup = useMatchup(leagueId, week);
  const lineup = useLineup(leagueId, week);
  const accuracy = useAccuracy(leagueId);

  return (
    <Gate query={matchup} noRoster={(m) => m.me.starters.length === 0}>
      {(m) => (
        <>
          <TitleRow title={`Week ${m.week}`} note={statusLine(m)} />
          <ScoreHero matchup={m} />
          {lineup.data && <HeadsUp lineup={lineup.data} />}
          <Link
            href="/lineup"
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-[14px] bg-accent p-3 font-extrabold text-on-accent hover:brightness-105"
          >
            {lineup.data && lineup.data.swaps.length > 0
              ? `Fix my lineup (${lineup.data.swaps.length}) →`
              : "Check my lineup →"}
          </Link>
          <AccuracyCard accuracy={accuracy.data} />
        </>
      )}
    </Gate>
  );
}

function HeadsUp({ lineup }: { lineup: Schemas["LineupOut"] }) {
  const alerts = headsUp(lineup);
  if (alerts.length === 0) return null;
  return (
    <Section title="Heads up">
      <div className="flex flex-col gap-2">
        {alerts.map((a, i) => (
          <div
            key={a.key}
            className="animate-fade-up flex items-center gap-3 rounded-[1.1rem] bg-raised px-3.5 py-3 shadow-card"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            <PlayerAvatar
              name={a.player.name}
              team={a.player.nfl_team}
              position={a.player.position}
              imageUrl={a.player.headshot_url}
              size={36}
            />
            <div className="min-w-0">
              <p
                className={cn(
                  "text-[0.9rem] font-semibold",
                  a.tone === "bad" && "text-bad",
                  a.tone === "good" && "text-good",
                )}
              >
                {a.title}
              </p>
              <small className="text-[0.78rem] text-ink-lo">{a.detail}</small>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}

function AccuracyCard({ accuracy }: { accuracy: Schemas["AccuracyOut"] | undefined }) {
  return (
    <Section title="How we've been doing">
      <Link href="/accuracy" className="block">
        <Card className="animate-fade-up flex items-center gap-3.5 hover:bg-overlay">
          {accuracy && accuracy.n > 0 && accuracy.coverage_80 != null ? (
            <>
              <Ring
                value={accuracy.coverage_80}
                size={46}
                stroke={5}
                label=""
                tone={Math.abs(accuracy.coverage_80 - 0.8) <= 0.1 ? "good" : "ok"}
              />
              <div>
                <span className="stat text-[1.6rem]">{f1(accuracy.mae)}</span>{" "}
                <small className="text-[0.78rem] text-ink-lo">
                  points off on a typical player · {pct(accuracy.coverage_80)} landed inside our 80% range
                  ({accuracy.n} graded)
                </small>
              </div>
            </>
          ) : (
            <p className="text-sm text-ink-lo">
              No graded weeks yet. After a week&apos;s games are final, we compare the projections we
              froze at kickoff with what actually happened, and the result shows up here.
            </p>
          )}
        </Card>
      </Link>
    </Section>
  );
}

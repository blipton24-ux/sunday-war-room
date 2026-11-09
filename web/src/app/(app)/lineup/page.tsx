"use client";

import { useLeague } from "@/components/league-context";
import { LineupCheck, TopPerformers } from "@/components/lineup";
import { ScoreHero } from "@/components/matchup";
import { PlayerRow } from "@/components/player/player-row";
import { Gate, TitleRow } from "@/components/screen";
import { Section } from "@/components/ui/primitives";
import { useLineup, useMatchup } from "@/lib/api/queries";

export default function LineupPage() {
  const { leagueId, week } = useLeague();
  const lineup = useLineup(leagueId, week);
  const matchup = useMatchup(leagueId, week);

  return (
    <Gate query={lineup} noRoster={(l) => l.starters.length === 0 && l.bench.length === 0}>
      {(l) => {
        const recommended = new Set(l.swaps.map((s) => s.player_in.player_id));
        return (
          <>
            <TitleRow title="Lineup" note="tap a player for the details" />
            {matchup.data && <ScoreHero matchup={matchup.data} />}
            <LineupCheck lineup={l} />
            <TopPerformers starters={l.starters} />
            <Section title="Starters">
              <div className="flex flex-col gap-1.5">
                {l.starters.map((p, i) => (
                  <PlayerRow key={p.player_id} player={p} leagueId={l.league_id} week={l.week} index={i} />
                ))}
              </div>
            </Section>
            {l.bench.length > 0 && (
              <Section title="Bench">
                <div className="flex flex-col gap-1.5">
                  {l.bench.map((p, i) => (
                    <PlayerRow
                      key={p.player_id}
                      player={p}
                      leagueId={l.league_id}
                      week={l.week}
                      index={i}
                      dim
                      recommended={recommended.has(p.player_id)}
                    />
                  ))}
                </div>
              </Section>
            )}
          </>
        );
      }}
    </Gate>
  );
}

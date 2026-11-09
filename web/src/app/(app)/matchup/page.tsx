"use client";

import { useLeague } from "@/components/league-context";
import { HeadToHead, MatchupBoard } from "@/components/matchup";
import { Gate, TitleRow } from "@/components/screen";
import { Section } from "@/components/ui/primitives";
import { useMatchup } from "@/lib/api/queries";
import { timeAgo } from "@/lib/format";

export default function MatchupPage() {
  const { leagueId, week } = useLeague();
  const matchup = useMatchup(leagueId, week);
  return (
    <Gate query={matchup} noRoster={(m) => m.me.starters.length === 0}>
      {(m) => (
        <>
          <TitleRow title="Matchup" note={`Week ${m.week} · scores as of ${timeAgo(m.as_of)}`} />
          <MatchupBoard matchup={m} />
          <Section title="Starters">
            <HeadToHead matchup={m} />
          </Section>
          {m.unsupported_rules.length > 0 && (
            <p className="px-1 text-xs text-ink-lo">
              Not scored yet in projections: {m.unsupported_rules.join(", ")}. These league rules
              need stats our data source doesn&apos;t provide.
            </p>
          )}
        </>
      )}
    </Gate>
  );
}

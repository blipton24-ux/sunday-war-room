"use client";

import { Target } from "lucide-react";

import { useLeague } from "@/components/league-context";
import { Gate, TitleRow } from "@/components/screen";
import { Card, EmptyState, Section } from "@/components/ui/primitives";
import { useAccuracy } from "@/lib/api/queries";
import { f1, pct } from "@/lib/format";
import { positionLabel } from "@/lib/positions";

export default function AccuracyPage() {
  const { leagueId } = useLeague();
  const accuracy = useAccuracy(leagueId);
  return (
    <Gate query={accuracy}>
      {(a) => (
        <>
          <TitleRow title="Accuracy" note={`model ${a.model_version}`} />
          <Card>
            <p className="text-sm text-ink-mid">
              Every projection is <b className="text-ink">frozen when the player&apos;s game kicks off</b>.
              After the games are final we compare those frozen numbers with what actually happened.
              Only projections made <b className="text-ink">before kickoff</b> count, so nothing here uses
              hindsight.
            </p>
          </Card>
          {a.n === 0 ? (
            <EmptyState icon={Target} title="No graded weeks yet">
              The first grades appear once a week&apos;s games are final and we have projections that
              were made before those games started.
            </EmptyState>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Typical miss" value={`${f1(a.mae)} pts`} hint="average gap between projection and result" />
                <Stat label="Inside 80% range" value={pct(a.coverage_80)} hint="should be close to 80%" />
                <Stat
                  label="Lean"
                  value={`${a.bias! >= 0 ? "+" : ""}${f1(a.bias)}`}
                  hint={a.bias! >= 0 ? "projections ran high" : "projections ran low"}
                />
              </div>
              <Section title="By position">
                <Card className="p-0">
                  <Table
                    head={["Position", "Players", "Typical miss", "Inside range"]}
                    rows={Object.entries(a.by_position).map(([pos, v]) => [
                      positionLabel(pos),
                      String(v.n ?? 0),
                      `${f1(v.mae)} pts`,
                      pct(v.coverage_80),
                    ])}
                  />
                </Card>
              </Section>
              <Section title="Week by week">
                <Card className="p-0">
                  <Table
                    head={["Week", "Players", "Typical miss", "Inside range"]}
                    rows={a.weeks.map((w) => [`Week ${w.week}`, String(w.n), `${f1(w.mae)} pts`, pct(w.coverage_80)])}
                  />
                </Card>
              </Section>
            </>
          )}
        </>
      )}
    </Gate>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Card className="p-3">
      <div className="text-[0.7rem] font-semibold text-sea">{label}</div>
      <div className="stat mt-1 text-xl">{value}</div>
      <div className="mt-1 text-[0.66rem] text-ink-faint">{hint}</div>
    </Card>
  );
}

function Table({ head, rows }: { head: string[]; rows: string[][] }) {
  return (
    <table className="nums w-full text-sm">
      <thead>
        <tr className="text-left text-[0.72rem] text-ink-lo">
          {head.map((h) => (
            <th key={h} className="px-4 py-2.5 font-semibold">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r[0]} className="border-t border-line">
            {r.map((c, i) => (
              <td key={i} className="px-4 py-2.5">
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

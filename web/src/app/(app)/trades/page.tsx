"use client";

import { ArrowLeftRight, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useLeague } from "@/components/league-context";
import { PlayerAvatar } from "@/components/player/avatar";
import { Gate, TitleRow } from "@/components/screen";
import { Card, Chip, EmptyState, PrimaryButton, Section } from "@/components/ui/primitives";
import { isApiError, type Schemas } from "@/lib/api/client";
import { useEvaluateTrade, useTradeIdeas, useTradeRosters } from "@/lib/api/queries";
import { cn } from "@/lib/cn";
import { f1, signed } from "@/lib/format";
import { positionLabel, slotLabel } from "@/lib/positions";

type Rosters = Schemas["TradeRostersOut"];
type Team = Schemas["TradeTeam"];
type Ref = Schemas["PlayerRef"];
type Idea = Schemas["TradeIdeaOut"];
type Side = Schemas["TradeSideOut"];

export default function TradesPage() {
  const { leagueId } = useLeague();
  const rosters = useTradeRosters(leagueId);
  const [draft, setDraft] = useState<Draft | null>(null);

  return (
    <Gate query={rosters}>
      {(r) => (
        <>
          <TitleRow title="Trades" note={titleNote(r)} />
          {!r.ready ? (
            <EmptyState icon={Users} title="Projecting rosters">
              Rest-of-season values are worked out after each sync. Refresh the league, or check back in a minute.
            </EmptyState>
          ) : (
            <>
              <Ideas leagueId={r.league_id} onOpen={setDraft} />
              {r.teams.length >= 2 && <Analyzer rosters={r} draft={draft} />}
            </>
          )}
        </>
      )}
    </Gate>
  );
}

function titleNote(r: Rosters): string {
  const parts: string[] = [];
  if (r.league_kind !== "redraft") parts.push("this-season value only");
  if (!r.trades_allowed) parts.push("trades are off in this league");
  else if (r.trade_deadline) parts.push(r.deadline_passed ? "trade deadline passed" : `deadline week ${r.trade_deadline}`);
  return parts.join(" · ");
}

// --------------------------------------------------------------------------- ideas
function Ideas({ leagueId, onOpen }: { leagueId: number; onOpen: (d: Draft) => void }) {
  const [maxLoss, setMaxLoss] = useState(1);
  const ideas = useTradeIdeas(leagueId, maxLoss);
  return (
    <Section title="Ideas for you">
      <Card>
        <label htmlFor="max-loss" className="flex items-center justify-between gap-3 text-sm text-ink-mid">
          <span>How much the other team may lose</span>
          <b className="nums text-ink">{maxLoss === 0 ? "nothing" : `up to ${f1(maxLoss)} pts/wk`}</b>
        </label>
        <input
          id="max-loss"
          type="range"
          min={0}
          max={3}
          step={0.5}
          value={maxLoss}
          onChange={(e) => setMaxLoss(Number(e.target.value))}
          className="mt-3 w-full accent-[var(--color-accent)]"
        />
        <p className="mt-2 text-[0.72rem] text-ink-lo">
          Higher finds bigger wins for you, but the other manager is less likely to say yes.
        </p>
      </Card>
      <div className="mt-2 flex flex-col gap-1.5">
        {ideas.isLoading && !ideas.data ? (
          <Card>
            <p className="text-sm text-ink-mid">Looking through every roster…</p>
          </Card>
        ) : ideas.data && ideas.data.ideas.length > 0 ? (
          ideas.data.ideas.map((idea, i) => <IdeaCard key={i} idea={idea} onOpen={onOpen} />)
        ) : (
          <Card>
            <p className="text-sm text-ink-mid">
              No trade helps your lineup within that limit. Let the other team lose a little more, or try your own
              idea below.
            </p>
          </Card>
        )}
      </div>
    </Section>
  );
}

function names(players: Ref[]): string {
  return players.map((p) => p.name).join(" + ");
}

function IdeaCard({ idea, onOpen }: { idea: Idea; onOpen: (d: Draft) => void }) {
  return (
    <Card className="flex flex-col gap-2">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 text-sm">
          <div className="font-semibold">With {idea.other_team_name}</div>
          <div className="mt-1 text-ink-mid">
            You give <b className="text-ink">{names(idea.gives)}</b>
          </div>
          <div className="text-ink-mid">
            You get <b className="text-ink">{names(idea.gets)}</b>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="nums font-display text-lg font-extrabold text-good">{signed(idea.my_change_per_week)}</div>
          <div className="text-[0.66rem] text-ink-lo">pts/wk for you</div>
          <div className="nums mt-1 text-[0.72rem] text-ink-mid">them {signed(idea.their_change_per_week)}</div>
        </div>
      </div>
      <button
        type="button"
        onClick={() =>
          onOpen({
            otherTeamId: idea.other_team_id,
            mine: idea.gives.map((p) => p.player_id),
            theirs: idea.gets.map((p) => p.player_id),
          })
        }
        className="min-h-11 self-start rounded-full bg-overlay px-4 text-sm font-bold text-ink hover:bg-high"
      >
        Open in the analyzer
      </button>
    </Card>
  );
}

// --------------------------------------------------------------------------- analyzer
type Draft = { otherTeamId: number; mine: number[]; theirs: number[] };

function Analyzer({ rosters, draft }: { rosters: Rosters; draft: Draft | null }) {
  // The page only renders this with at least two teams.
  const mineTeam = rosters.teams.find((t) => t.is_mine) ?? rosters.teams[0]!;
  const others = rosters.teams.filter((t) => t.team_id !== mineTeam.team_id);
  const [aId, setAId] = useState(mineTeam.team_id);
  const [bId, setBId] = useState(others[0]?.team_id ?? mineTeam.team_id);
  const [aGives, setAGives] = useState<Set<number>>(new Set());
  const [bGives, setBGives] = useState<Set<number>>(new Set());
  const evaluate = useEvaluateTrade(rosters.league_id);

  // "Open in the analyzer" from an idea fills in both sides.
  useEffect(() => {
    if (!draft) return;
    /* eslint-disable react-hooks/set-state-in-effect -- an outside request to load a trade */
    setAId(mineTeam.team_id);
    setBId(draft.otherTeamId);
    setAGives(new Set(draft.mine));
    setBGives(new Set(draft.theirs));
    /* eslint-enable react-hooks/set-state-in-effect */
    evaluate.reset();
    document.getElementById("analyzer")?.scrollIntoView({ behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]);

  const byId = useMemo(() => new Map(rosters.teams.map((t) => [t.team_id, t])), [rosters.teams]);
  const a = byId.get(aId)!;
  const b = byId.get(bId)!;
  const ready = aId !== bId && aGives.size > 0 && bGives.size > 0;

  function pickTeam(which: "a" | "b", id: number) {
    evaluate.reset();
    if (which === "a") {
      setAId(id);
      setAGives(new Set());
    } else {
      setBId(id);
      setBGives(new Set());
    }
  }

  function toggle(which: "a" | "b", playerId: number) {
    evaluate.reset();
    const [set, setter] = which === "a" ? [aGives, setAGives] : [bGives, setBGives];
    const next = new Set(set);
    if (next.has(playerId)) next.delete(playerId);
    else next.add(playerId);
    setter(next);
  }

  return (
    <Section title="Analyze a trade" className="scroll-mt-24">
      <div id="analyzer" className="grid gap-2 md:grid-cols-2">
        <TeamPicker
          label="Team A"
          teams={rosters.teams}
          team={a}
          exclude={bId}
          selected={aGives}
          onTeam={(id) => pickTeam("a", id)}
          onToggle={(id) => toggle("a", id)}
        />
        <TeamPicker
          label="Team B"
          teams={rosters.teams}
          team={b}
          exclude={aId}
          selected={bGives}
          onTeam={(id) => pickTeam("b", id)}
          onToggle={(id) => toggle("b", id)}
        />
      </div>
      <div className="mt-3">
        <PrimaryButton
          disabled={!ready || evaluate.isPending}
          onClick={() =>
            evaluate.mutate({ team_a_id: aId, team_b_id: bId, a_gives: [...aGives], b_gives: [...bGives] })
          }
        >
          <ArrowLeftRight className="size-4" aria-hidden />
          {evaluate.isPending ? "Working it out…" : "Evaluate trade"}
        </PrimaryButton>
        {!ready && <p className="mt-2 text-[0.72rem] text-ink-lo">Pick at least one player on each side.</p>}
      </div>
      {evaluate.error && (
        <Card className="mt-3">
          <p className="text-sm text-bad">
            {isApiError(evaluate.error) ? evaluate.error.message : "Couldn't evaluate that trade."}
          </p>
        </Card>
      )}
      {evaluate.data && <TradeResult a={evaluate.data.a} b={evaluate.data.b} />}
    </Section>
  );
}

function TeamPicker({
  label,
  teams,
  team,
  exclude,
  selected,
  onTeam,
  onToggle,
}: {
  label: string;
  teams: Team[];
  team: Team;
  exclude: number;
  selected: Set<number>;
  onTeam: (id: number) => void;
  onToggle: (playerId: number) => void;
}) {
  const id = `team-${label.replace(" ", "-").toLowerCase()}`;
  return (
    <Card className="p-3">
      <label htmlFor={id} className="eyebrow block">
        {label} gives
      </label>
      <select
        id={id}
        value={team.team_id}
        onChange={(e) => onTeam(Number(e.target.value))}
        className="mt-1 min-h-11 w-full rounded-xl bg-overlay px-3 text-sm font-semibold text-ink"
      >
        {teams
          .filter((t) => t.team_id !== exclude)
          .map((t) => (
            <option key={t.team_id} value={t.team_id}>
              {t.name}
              {t.is_mine ? " (you)" : ""}
            </option>
          ))}
      </select>
      <ul className="mt-2 flex max-h-80 flex-col gap-1 overflow-y-auto pr-1">
        {team.players.map((rp) => {
          const p = rp.player;
          const checked = selected.has(p.player_id);
          return (
            <li key={p.player_id}>
              <label
                className={cn(
                  "flex min-h-11 cursor-pointer items-center gap-2.5 rounded-xl px-2 py-1 hover:bg-overlay",
                  checked && "bg-overlay",
                )}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(p.player_id)}
                  className="size-4 accent-[var(--color-accent)]"
                />
                <PlayerAvatar name={p.name} team={p.nfl_team} position={p.position} imageUrl={p.headshot_url} size={32} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-semibold">{p.name}</span>
                  <span className="text-[0.68rem] text-ink-lo">
                    {positionLabel(p.position)} · {slotLabel(rp.slot)}
                  </span>
                </span>
                <span className="nums text-[0.72rem] text-ink-mid">{f1(rp.points_per_week)}/wk</span>
              </label>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}

function TradeResult({ a, b }: { a: Side; b: Side }) {
  return (
    <div className="mt-3 grid gap-2 md:grid-cols-2" aria-live="polite">
      <SideCard side={a} />
      <SideCard side={b} />
    </div>
  );
}

function SideCard({ side }: { side: Side }) {
  const tone = side.change_per_week > 0.05 ? "text-good" : side.change_per_week < -0.05 ? "text-bad" : "text-ink";
  const before = new Set(side.lineup_before.map((s) => s.player?.player_id));
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate font-semibold">{side.name}</div>
          <div className="mt-1 text-[0.72rem] text-ink-lo">
            best lineup {f1(side.before_per_week)} → {f1(side.after_per_week)} pts/wk
          </div>
        </div>
        <div className="text-right">
          <div className={cn("nums font-display text-2xl font-extrabold", tone)}>{signed(side.change_per_week)}</div>
          <div className="text-[0.66rem] text-ink-lo">pts/wk</div>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {side.gets.map((p) => (
          <Chip key={p.player_id} tone="good">
            gets {p.name}
          </Chip>
        ))}
        {side.gives.map((p) => (
          <Chip key={p.player_id} tone="neutral">
            gives {p.name}
          </Chip>
        ))}
        {side.dropped.map((p) => (
          <Chip key={p.player_id} tone="warn">
            must drop {p.name}
          </Chip>
        ))}
      </div>
      <h4 className="eyebrow mt-3">Lineup after</h4>
      <p className="mb-1 text-[0.68rem] text-ink-lo">
        A typical week. Gains also count weeks a player covers a bye or injury, so a backup can add value without
        appearing here.
      </p>
      <ul className="flex flex-col gap-0.5 text-sm">
        {side.lineup_after.map((s, i) => (
          <li key={i} className="flex items-center justify-between gap-2">
            <span className="flex min-w-0 items-center gap-2">
              <span className="w-10 shrink-0 text-[0.66rem] font-bold text-ink-lo">{slotLabel(s.slot)}</span>
              <span className={cn("truncate", s.player && !before.has(s.player.player_id) && "font-semibold text-good")}>
                {s.player?.name ?? "empty"}
              </span>
            </span>
            <span className="nums text-[0.72rem] text-ink-mid">{f1(s.points_per_week)}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

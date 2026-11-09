import { f1 } from "@/lib/format";

/**
 * Bust → Proj → Boom bar (ADR-032): solid segments for the 10th–90th percentile range,
 * a tick at the projection, and a dot at the actual score once the game is final.
 */
export function RangeBar({
  p10,
  points,
  p90,
  actual,
}: {
  p10: number;
  points: number;
  p90: number;
  actual: number | null;
}) {
  const lo = Math.min(0, p10, actual ?? 0);
  const hi = Math.max(p90, points, actual ?? 0) * 1.12 || 1;
  const at = (x: number) => Math.max(0, Math.min(100, ((x - lo) / (hi - lo)) * 100));
  const p25 = p10 + (points - p10) * 0.55;
  const p75 = points + (p90 - points) * 0.45;
  return (
    <div>
      <div className="relative pt-5">
        {actual != null && (
          <span
            className="nums absolute top-0 -translate-x-1/2 rounded-full bg-ink px-1.5 text-[0.62rem] font-bold leading-4 text-base"
            style={{ left: `${at(actual)}%` }}
          >
            {f1(actual)}
          </span>
        )}
        <div
          className="relative h-2.5 rounded-full bg-high"
          role="img"
          aria-label={`Range ${f1(p10)} to ${f1(p90)}, projection ${f1(points)}${actual != null ? `, scored ${f1(actual)}` : ""}`}
        >
          <div
            className="absolute inset-y-0 rounded-l-full bg-ember/55"
            style={{ left: `${at(p10)}%`, width: `${at(p25) - at(p10)}%` }}
          />
          <div
            className="absolute inset-y-0 bg-accent/75"
            style={{ left: `${at(p25)}%`, width: `${at(p75) - at(p25)}%` }}
          />
          <div
            className="absolute inset-y-0 rounded-r-full bg-good/55"
            style={{ left: `${at(p75)}%`, width: `${at(p90) - at(p75)}%` }}
          />
          <div
            className="absolute -inset-y-1 w-0.5 rounded-sm bg-ink"
            style={{ left: `${at(points)}%` }}
          />
          {actual != null && (
            <div
              className="absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-base bg-ink"
              style={{ left: `${at(actual)}%` }}
            />
          )}
        </div>
      </div>
      <div className="mt-2 flex justify-between text-[0.7rem]">
        <span className="text-ember">
          Bust <b className="nums">{f1(p10)}</b>
        </span>
        <span className="text-ink-lo">
          Proj <b className="nums text-ink">{f1(points)}</b>
        </span>
        <span className="text-good">
          Boom <b className="nums">{f1(p90)}</b>
        </span>
      </div>
    </div>
  );
}

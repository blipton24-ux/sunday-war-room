/** Sunday War Room mark (flat): a war-room table from above, the ball under the lamp. */
export function Logo({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label="Sunday War Room"
      className={className}
    >
      <rect width="100" height="100" rx="22" fill="#141e28" />
      <g fill="#34495c">
        {[22, 37, 52, 67].map((x) => (
          <rect key={`t${x}`} x={x} y="22" width="11" height="7" rx="2.5" />
        ))}
        {[22, 37, 52, 67].map((x) => (
          <rect key={`b${x}`} x={x} y="71" width="11" height="7" rx="2.5" />
        ))}
        <rect x="7" y="44" width="7" height="12" rx="2.5" />
        <rect x="86" y="44" width="7" height="12" rx="2.5" />
      </g>
      <rect x="16" y="32" width="68" height="36" rx="18" fill="#1d2c3a" stroke="#e6b95c" strokeWidth="2.5" />
      <g stroke="#efe8da" strokeOpacity=".16" strokeWidth="1">
        <line x1="30" y1="35" x2="30" y2="65" />
        <line x1="40" y1="34" x2="40" y2="66" />
        <line x1="60" y1="34" x2="60" y2="66" />
        <line x1="70" y1="35" x2="70" y2="65" />
      </g>
      <circle cx="50" cy="50" r="17" fill="#e6b95c" fillOpacity=".12" />
      <ellipse cx="50" cy="50" rx="12" ry="7.5" fill="#e6b95c" transform="rotate(-25 50 50)" />
      <g stroke="#0f1720" strokeWidth="1.4" strokeLinecap="round" transform="rotate(-25 50 50)">
        <line x1="44.5" y1="50" x2="55.5" y2="50" />
        <line x1="47" y1="48" x2="47" y2="52" />
        <line x1="50" y1="48" x2="50" y2="52" />
        <line x1="53" y1="48" x2="53" y2="52" />
      </g>
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="whitespace-nowrap font-display text-[1.05rem] font-black tracking-tight [font-stretch:118%]">
      Sunday <b className="font-black text-accent">War Room</b>
    </span>
  );
}

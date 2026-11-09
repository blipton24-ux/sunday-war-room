"use client";

import Image from "next/image";
import { useState } from "react";

import { cn } from "@/lib/cn";
import { initials } from "@/lib/format";
import { slotBg, slotLabel } from "@/lib/positions";
import { teamColor, tint } from "@/lib/teams";

/**
 * Headshot on a flat tint of the team color, slot tag pinned bottom-left (ADR-032).
 * Images go through the Next.js image cache (ADR-037); any failure shows initials.
 */
export function PlayerAvatar({
  name,
  team,
  position,
  imageUrl,
  slot,
  size = 46,
  mirror = false,
}: {
  name: string;
  team: string | null;
  position: string | null;
  imageUrl: string | null;
  slot?: string;
  size?: number;
  mirror?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  const color = teamColor(team);
  const isLogo = position === "DEF";
  return (
    <span className="relative inline-block shrink-0">
      <span
        className="relative grid place-items-center overflow-hidden rounded-full"
        style={{
          width: size,
          height: size,
          background: tint(color, 0.25),
          boxShadow: `inset 0 0 0 1.5px ${tint(color, 0.4)}`,
        }}
      >
        {imageUrl && !failed ? (
          <Image
            src={imageUrl}
            alt=""
            width={isLogo ? Math.round(size * 0.72) : size * 2}
            height={isLogo ? Math.round(size * 0.72) : Math.round(size * 1.46)}
            sizes={`${size}px`}
            onError={() => setFailed(true)}
            className={cn(
              isLogo
                ? "object-contain"
                : "absolute bottom-0 left-1/2 h-[92%] w-auto max-w-none -translate-x-1/2",
            )}
          />
        ) : (
          <span
            className="font-display font-extrabold text-ink"
            style={{ fontSize: Math.round(size * 0.34) }}
          >
            {isLogo ? (team ?? "?") : initials(name)}
          </span>
        )}
      </span>
      {slot && (
        <span
          className={cn(
            "absolute -bottom-1 rounded-md px-1 text-[0.58rem] font-black leading-[1.15rem] text-[#0b1016]",
            mirror ? "-right-1" : "-left-1",
            slotBg(slot),
          )}
        >
          {slotLabel(slot)}
        </span>
      )}
    </span>
  );
}

/** A fantasy team's circular badge: two letters on its color. */
export function TeamBadge({ name, avatarUrl, color }: { name: string; avatarUrl?: string | null; color: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <span
      className="grid size-11 shrink-0 place-items-center overflow-hidden rounded-full font-display text-sm font-extrabold text-white shadow-[0_0_0_2px_var(--scrim)]"
      style={{ background: color }}
    >
      {avatarUrl && !failed ? (
        // Sleeper avatars are not in the image allow-list; a plain img keeps them out of our cache.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={avatarUrl} alt="" className="size-full object-cover" onError={() => setFailed(true)} />
      ) : (
        initials(name)
      )}
    </span>
  );
}

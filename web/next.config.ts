import type { NextConfig } from "next";

const config: NextConfig = {
  // Self-contained server bundle for the Docker image (P1 step 13).
  output: "standalone",
  poweredByHeader: false,
  images: {
    // ADR-037: player photos and team logos come only from these ESPN paths, through the
    // Next.js image cache (resized, cached; initials fallback in <PlayerAvatar>).
    remotePatterns: [
      { protocol: "https", hostname: "a.espncdn.com", pathname: "/i/headshots/nfl/players/full/**" },
      { protocol: "https", hostname: "a.espncdn.com", pathname: "/i/teamlogos/nfl/500/**" },
    ],
    minimumCacheTTL: 60 * 60 * 24 * 7, // a week: headshots rarely change
  },
};

export default config;

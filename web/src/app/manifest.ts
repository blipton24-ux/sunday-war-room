import type { MetadataRoute } from "next";

/**
 * Web app manifest (ADR-010): what makes the site installable to the home screen.
 * Served at /manifest.webmanifest. Colors match the dark theme's base surface (ADR-024) so
 * the splash screen doesn't flash a different color before the app paints.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Sunday War Room",
    short_name: "War Room",
    description:
      "Your fantasy football war room: start/sit calls, matchup odds and projections that explain themselves.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#0b1016",
    theme_color: "#0b1016",
    categories: ["sports"],
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      // Full-bleed, logo inside the safe zone: Android crops it to the phone's icon shape.
      { src: "/icons/maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    ],
    // Long-press the home-screen icon for quick links.
    shortcuts: [
      { name: "My lineup", short_name: "Lineup", url: "/lineup" },
      { name: "Matchup", short_name: "Matchup", url: "/matchup" },
    ],
  };
}

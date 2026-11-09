import type { Metadata, Viewport } from "next";
import { Archivo, Inter } from "next/font/google";

import { Providers } from "@/components/providers";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
// Variable width axis: the wide 112-118% stretch is part of the Sunday War Room look.
const archivo = Archivo({
  subsets: ["latin"],
  variable: "--font-archivo",
  axes: ["wdth"],
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Sunday War Room", template: "%s · Sunday War Room" },
  description: "Your fantasy football war room: start/sit, matchup odds and projections that explain themselves.",
  applicationName: "Sunday War Room",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0b1016" },
    { media: "(prefers-color-scheme: light)", color: "#f4efe4" },
  ],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // next-themes sets data-theme before paint; suppress the expected attribute mismatch.
    <html lang="en" suppressHydrationWarning className={`${inter.variable} ${archivo.variable}`}>
      <body className="font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

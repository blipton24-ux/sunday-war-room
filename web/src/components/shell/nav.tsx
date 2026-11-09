"use client";

import {
  ClipboardList,
  Ellipsis,
  House,
  type LucideIcon,
  MessageSquare,
  Swords,
  Target,
  TrendingUp,
  Users,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Menu, MenuContent, MenuItem, MenuTrigger } from "@/components/ui/menu";
import { cn } from "@/lib/cn";

interface Tab {
  href: string;
  label: string;
  icon: LucideIcon;
  phase?: string;
}

// ADR-025: Home · Lineup · Matchup · Chat · More (Waivers, Trades, Accuracy).
const MAIN: Tab[] = [
  { href: "/", label: "Home", icon: House },
  { href: "/lineup", label: "Lineup", icon: ClipboardList },
  { href: "/matchup", label: "Matchup", icon: Swords },
  { href: "/chat", label: "Chat", icon: MessageSquare, phase: "P3" },
];
const MORE: Tab[] = [
  { href: "/waivers", label: "Waivers", icon: TrendingUp, phase: "P2" },
  { href: "/trades", label: "Trades", icon: Users, phase: "P2" },
  { href: "/accuracy", label: "Accuracy", icon: Target },
];

function isActive(path: string, href: string): boolean {
  return href === "/" ? path === "/" : path.startsWith(href);
}

function MoreMenu({ children, align }: { children: React.ReactNode; align: "start" | "end" }) {
  const router = useRouter();
  const path = usePathname();
  return (
    <Menu>
      <MenuTrigger asChild>{children}</MenuTrigger>
      <MenuContent align={align} side={align === "end" ? "top" : "bottom"}>
        {MORE.map(({ href, label, icon: Icon, phase }) => (
          <MenuItem key={href} active={isActive(path, href)} onSelect={() => router.push(href)}>
            <span className="flex items-center gap-2.5">
              <Icon className="size-[18px]" />
              {label}
            </span>
            {phase && <span className="text-[0.65rem] font-semibold text-ink-faint">{phase}</span>}
          </MenuItem>
        ))}
      </MenuContent>
    </Menu>
  );
}

/** Desktop: pill tab bar under the header. */
export function PillNav() {
  const path = usePathname();
  const moreOn = MORE.some((t) => isActive(path, t.href));
  const pill = (on: boolean) =>
    cn(
      "flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-semibold text-ink-lo hover:text-ink-mid",
      on && "bg-high text-ink shadow-[inset_0_0_0_1px_rgb(var(--accent-rgb)/0.3)] [&_svg]:text-accent",
    );
  return (
    <nav className="sticky top-[calc(61px+env(safe-area-inset-top))] z-30 hidden bg-base sm:block" aria-label="Main">
      <div className="mx-auto max-w-5xl px-4 py-2">
        <div className="inline-flex gap-1 rounded-full bg-raised p-1">
          {MAIN.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className={pill(isActive(path, href))}>
              <Icon className="size-[18px]" />
              {label}
            </Link>
          ))}
          <MoreMenu align="start">
            <button className={pill(moreOn)}>
              <Ellipsis className="size-[18px]" />
              More
            </button>
          </MoreMenu>
        </div>
      </div>
    </nav>
  );
}

/** Phone: bottom tab bar, thumb-reachable (ADR-025). */
export function BottomNav() {
  const path = usePathname();
  const moreOn = MORE.some((t) => isActive(path, t.href));
  const item = (on: boolean) =>
    cn(
      "flex min-h-14 flex-col items-center gap-1 pb-1.5 text-[0.68rem] font-medium text-ink-lo",
      on && "text-ink [&_.pill]:accent-soft [&_.pill]:text-accent",
    );
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 border-t border-accent/15 bg-base pb-[env(safe-area-inset-bottom)] sm:hidden"
      aria-label="Main"
    >
      <div className="grid grid-cols-5 px-1 pt-1.5">
        {MAIN.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href} className={item(isActive(path, href))}>
            <span className="pill grid h-7 w-12 place-items-center rounded-full">
              <Icon className="size-[18px]" />
            </span>
            {label}
          </Link>
        ))}
        <MoreMenu align="end">
          <button className={item(moreOn)}>
            <span className="pill grid h-7 w-12 place-items-center rounded-full">
              <Ellipsis className="size-[18px]" />
            </span>
            More
          </button>
        </MoreMenu>
      </div>
    </nav>
  );
}

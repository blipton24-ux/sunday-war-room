/**
 * Small building blocks from the Sunday War Room mockup (v3): cards separate from the page
 * by surface level, never by borders; chips; skeletons; empty and error states.
 */
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

export function Card({
  className,
  glow,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { glow?: boolean }) {
  return (
    <div
      className={cn("rounded-[1.25rem] bg-raised p-4 shadow-card", glow && "accent-ring", className)}
      {...props}
    />
  );
}

export function Section({
  title,
  className,
  children,
}: {
  title?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section className={className}>
      {title && <h3 className="eyebrow">{title}</h3>}
      {children}
    </section>
  );
}

type ChipTone = "dim" | "live" | "final" | "accent" | "neutral" | "good" | "warn" | "bad";

const CHIP: Record<ChipTone, string> = {
  dim: "bg-scrim text-ink-mid",
  live: "bg-ember/15 text-ember",
  final: "bg-high text-ink-lo",
  accent: "accent-soft text-accent",
  neutral: "bg-high text-ink-mid",
  good: "bg-good/15 text-good",
  warn: "bg-warn/15 text-warn",
  bad: "bg-bad/15 text-bad",
};

export function Chip({
  tone = "dim",
  className,
  children,
}: {
  tone?: ChipTone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[0.66rem] font-bold",
        CHIP[tone],
        className,
      )}
    >
      {tone === "live" && <i className="animate-live size-1.5 rounded-full bg-ember" />}
      {children}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-[1.25rem] bg-raised", className)} />;
}

export function ScreenSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="h-44" />
      <Skeleton className="h-24" />
      <Skeleton className="h-16" />
      <Skeleton className="h-16" />
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: LucideIcon;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="px-5 py-12 text-center text-ink-lo">
      <div className="accent-soft mx-auto mb-3 grid size-14 place-items-center rounded-full text-accent">
        <Icon className="size-6" aria-hidden />
      </div>
      <h3 className="mb-1.5 font-display text-lg font-extrabold text-ink [font-stretch:112%]">
        {title}
      </h3>
      {children && <div className="mx-auto max-w-sm text-sm">{children}</div>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <Card className="text-center">
      <p className="font-semibold text-bad">{title}</p>
      {message && <p className="mt-1 text-sm text-ink-lo">{message}</p>}
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded-full bg-high px-4 py-2 text-sm font-semibold text-ink-mid hover:text-ink"
        >
          Try again
        </button>
      )}
    </Card>
  );
}

export function PrimaryButton({
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "flex min-h-11 w-full items-center justify-center gap-2 rounded-[14px] bg-accent px-4 py-3 font-extrabold text-on-accent hover:brightness-105 disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

export function SecondaryButton({
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "flex min-h-11 items-center justify-center gap-2 rounded-[14px] bg-high px-4 py-2.5 text-sm font-semibold text-ink-mid hover:text-ink disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
}

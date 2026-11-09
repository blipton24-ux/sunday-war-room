"use client";

/**
 * Dropdown menu and confirm dialog in the shadcn/ui style (ADR-012): Radix primitives for
 * keyboard and screen-reader behavior, styled with Sunday War Room tokens.
 */
import { AlertDialog as AD, DropdownMenu as DM } from "radix-ui";

import { cn } from "@/lib/cn";

export const Menu = DM.Root;
export const MenuTrigger = DM.Trigger;

export function MenuContent({ className, ...props }: DM.DropdownMenuContentProps) {
  return (
    <DM.Portal>
      <DM.Content
        sideOffset={8}
        align="start"
        className={cn(
          "z-50 min-w-52 rounded-[1.1rem] bg-high p-1.5 shadow-pop outline-none animate-fade-up",
          className,
        )}
        {...props}
      />
    </DM.Portal>
  );
}

export function MenuItem({
  className,
  active,
  ...props
}: DM.DropdownMenuItemProps & { active?: boolean }) {
  return (
    <DM.Item
      className={cn(
        "flex min-h-10 cursor-pointer select-none items-center justify-between gap-3 rounded-xl px-3 py-2 text-sm font-semibold text-ink-mid outline-none data-[highlighted]:bg-overlay data-[highlighted]:text-ink",
        active && "accent-soft text-accent",
        className,
      )}
      {...props}
    />
  );
}

export function MenuSeparator() {
  return <DM.Separator className="my-1 h-px bg-line-strong" />;
}

// --------------------------------------------------------------------------- confirm dialog
export function ConfirmDialog({
  trigger,
  title,
  description,
  confirmLabel,
  onConfirm,
  busy,
}: {
  trigger: React.ReactNode;
  title: string;
  description: React.ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  busy?: boolean;
}) {
  return (
    <AD.Root>
      <AD.Trigger asChild>{trigger}</AD.Trigger>
      <AD.Portal>
        <AD.Overlay className="fixed inset-0 z-50 bg-black/50" />
        <AD.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-[1.25rem] bg-raised p-5 shadow-pop">
          <AD.Title className="font-display text-lg font-extrabold [font-stretch:112%]">
            {title}
          </AD.Title>
          <AD.Description className="mt-2 text-sm text-ink-lo">{description}</AD.Description>
          <div className="mt-5 flex justify-end gap-2">
            <AD.Cancel className="min-h-11 rounded-[14px] bg-high px-4 text-sm font-semibold text-ink-mid">
              Cancel
            </AD.Cancel>
            <AD.Action
              onClick={onConfirm}
              disabled={busy}
              className="min-h-11 rounded-[14px] bg-bad px-4 text-sm font-bold text-white disabled:opacity-50"
            >
              {confirmLabel}
            </AD.Action>
          </div>
        </AD.Content>
      </AD.Portal>
    </AD.Root>
  );
}

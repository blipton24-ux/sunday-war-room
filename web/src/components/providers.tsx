"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { useState } from "react";

import { isApiError } from "@/lib/api/client";
import { ToastProvider } from "@/components/ui/toast";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: true,
            // Don't retry what won't change: not found, not ready, signed out, rate limited.
            retry: (count, error) =>
              !(isApiError(error) && [401, 404, 409, 422, 429].includes(error.status)) &&
              count < 2,
          },
        },
      }),
  );
  return (
    // ADR-024: dark by default, the phone's setting respected on first visit, toggle in header.
    <ThemeProvider attribute="data-theme" defaultTheme="system" enableSystem>
      <QueryClientProvider client={queryClient}>
        <ToastProvider>{children}</ToastProvider>
      </QueryClientProvider>
    </ThemeProvider>
  );
}

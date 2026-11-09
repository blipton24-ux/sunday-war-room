import { Users } from "lucide-react";

import { EmptyState } from "@/components/ui/primitives";

export const metadata = { title: "Trades" };

export default function Page() {
  return (
    <EmptyState icon={Users} title="Trades">
      Coming in Phase 2: any trade evaluated for both sides.
    </EmptyState>
  );
}

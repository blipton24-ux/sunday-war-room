import { TrendingUp } from "lucide-react";

import { EmptyState } from "@/components/ui/primitives";

export const metadata = { title: "Waivers" };

export default function Page() {
  return (
    <EmptyState icon={TrendingUp} title="Waivers">
      Coming in Phase 2: free agents ranked by what they would add to your roster.
    </EmptyState>
  );
}

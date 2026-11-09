import { MessageSquare } from "lucide-react";

import { EmptyState } from "@/components/ui/primitives";

export const metadata = { title: "Ask the war room" };

export default function Page() {
  return (
    <EmptyState icon={MessageSquare} title="Ask the war room">
      Coming in Phase 3: questions like &ldquo;Should I start Robinson or Pacheco?&rdquo; answered from your league&apos;s real data.
    </EmptyState>
  );
}

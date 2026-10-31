import { FlaskConical } from "lucide-react";

export function SimulatedBadge() {
  return (
    <div className="flex items-center justify-center gap-1.5 border-t bg-muted/50 px-3 py-1.5 text-center text-[11px] text-muted-foreground">
      <FlaskConical className="h-3 w-3" />
      Prototype - synthetic data - simulated bank - demo signing key
    </div>
  );
}

import type { ReactNode } from "react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useAuth } from "@/lib/AuthContext";

/** Renders children only when the current user's role is allowed; otherwise renders a disabled
 * clone with a tooltip explaining the rule — the server still enforces this regardless. */
export function RoleGate({
  allow,
  reason,
  children,
}: {
  allow: string[];
  reason?: string;
  children: ReactNode;
}) {
  const { user } = useAuth();
  const allowed = !!user && allow.includes(user.role);

  if (allowed) return <>{children}</>;

  const disabledReason = reason ?? `Only ${allow.join(", ")} can do this.`;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-block cursor-not-allowed opacity-50 [&_button]:pointer-events-none [&_a]:pointer-events-none">
          {children}
        </span>
      </TooltipTrigger>
      <TooltipContent>{disabledReason}</TooltipContent>
    </Tooltip>
  );
}

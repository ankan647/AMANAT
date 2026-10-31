import type { ReactNode } from "react";
import { HelpCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";

export function ExplainDrawer({
  title = "Why this?",
  trigger,
  steps,
}: {
  title?: string;
  trigger?: ReactNode;
  steps: { label: string; detail: string | null }[];
}) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        {trigger ?? (
          <Button variant="outline" size="sm" className="gap-1.5">
            <HelpCircle className="h-3.5 w-3.5" />
            Why this?
          </Button>
        )}
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
        </SheetHeader>
        <ol className="mt-4 space-y-4">
          {steps.map((step, i) => (
            <li key={i} className="relative border-l-2 border-indigo-200 pl-4 dark:border-indigo-900">
              <div className="absolute -left-[5px] top-1 h-2 w-2 rounded-full bg-indigo-500" />
              <p className="text-sm font-medium">{step.label}</p>
              {step.detail && <p className="mt-0.5 text-sm text-muted-foreground">{step.detail}</p>}
            </li>
          ))}
        </ol>
      </SheetContent>
    </Sheet>
  );
}

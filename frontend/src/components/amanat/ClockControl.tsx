import { useState } from "react";
import { CalendarClock, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Separator } from "@/components/ui/separator";
import { useAdvanceClock, useClock, useResetClock } from "@/api/hooks/useClock";

export function ClockControl() {
  const { data } = useClock();
  const advance = useAdvanceClock();
  const reset = useResetClock();
  const [open, setOpen] = useState(false);

  const simulatedNow = data?.data.simulated_now ? new Date(data.data.simulated_now) : null;

  async function doAdvance(days: number) {
    try {
      const result = await advance.mutateAsync(days);
      const { reminders, escalations, bank_overdue } = result.data.fired;
      const parts = [];
      if (reminders) parts.push(`${reminders} reminder${reminders === 1 ? "" : "s"} fired`);
      if (escalations) parts.push(`${escalations} escalation${escalations === 1 ? "" : "s"}`);
      if (bank_overdue) parts.push(`${bank_overdue} bank overdue`);
      toast.success(`Advanced ${days} day${days === 1 ? "" : "s"}`, {
        description: parts.length ? parts.join(", ") : "No reminders due in this window.",
      });
      setOpen(false);
    } catch {
      toast.error("Could not advance the clock.");
    }
  }

  async function doReset() {
    await reset.mutateAsync();
    toast.info("Clock reset to the simulation start date.");
    setOpen(false);
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <CalendarClock className="h-4 w-4" />
          {simulatedNow ? simulatedNow.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }) : "—"}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-56">
        <p className="mb-2 text-xs font-medium text-muted-foreground">Advance simulated clock</p>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => doAdvance(1)} disabled={advance.isPending}>
            +1 day
          </Button>
          <Button size="sm" variant="secondary" onClick={() => doAdvance(7)} disabled={advance.isPending}>
            +7
          </Button>
          <Button size="sm" variant="secondary" onClick={() => doAdvance(30)} disabled={advance.isPending}>
            +30
          </Button>
        </div>
        <Separator className="my-3" />
        <Button size="sm" variant="ghost" className="w-full justify-start gap-2" onClick={doReset}>
          <RotateCcw className="h-3.5 w-3.5" />
          Reset to start date
        </Button>
      </PopoverContent>
    </Popover>
  );
}

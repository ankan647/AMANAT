import { motion } from "framer-motion";
import { Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/amanat/EmptyState";
import { useActivity } from "@/api/hooks/useDashboard";
import { formatDateTime } from "@/lib/dates";

export function ActivityFeed() {
  const { data, isLoading } = useActivity(20);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        )}
        {!isLoading && (!data || data.length === 0) && (
          <EmptyState icon={Activity} title="No activity yet" description="Actions will appear here as officers work." />
        )}
        {!isLoading && data && data.length > 0 && (
          <ul className="space-y-3">
            {data.map((event, i) => (
              <motion.li
                key={event.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                className="flex items-start gap-2 text-sm"
              >
                <div className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500" />
                <div>
                  <p>{event.message}</p>
                  <p className="text-xs text-muted-foreground">{formatDateTime(event.ts)}</p>
                </div>
              </motion.li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useMarkAllNotificationsRead, useMarkNotificationRead, useNotifications } from "@/api/hooks/useReminders";
import { formatDateTime } from "@/lib/dates";

export function NotificationBell() {
  const { data } = useNotifications();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();
  const [bounce, setBounce] = useState(false);
  const prevUnread = useRef<number>(0);

  const notifications = data?.data ?? [];
  const unread = notifications.filter((n) => !n.read_at).length;

  useEffect(() => {
    if (unread > prevUnread.current) {
      setBounce(true);
      const t = setTimeout(() => setBounce(false), 600);
      return () => clearTimeout(t);
    }
    prevUnread.current = unread;
  }, [unread]);

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <motion.div animate={bounce ? { y: [0, -4, 0] } : {}} transition={{ duration: 0.4 }}>
            <Bell className="h-4 w-4" />
          </motion.div>
          {unread > 0 && (
            <span className="absolute right-1 top-1 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-medium text-white">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="flex items-center justify-between border-b p-3">
          <p className="text-sm font-medium">Notifications</p>
          {unread > 0 && (
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => markAllRead.mutate()}>
              Mark all read
            </Button>
          )}
        </div>
        <div className="max-h-80 overflow-y-auto">
          {notifications.length === 0 && (
            <p className="p-4 text-center text-sm text-muted-foreground">No notifications yet.</p>
          )}
          {notifications.slice(0, 20).map((n) => (
            <button
              key={n.id}
              onClick={() => !n.read_at && markRead.mutate(n.id)}
              className={`w-full border-b px-3 py-2 text-left text-sm last:border-b-0 hover:bg-muted/50 ${
                n.read_at ? "text-muted-foreground" : "font-medium"
              }`}
            >
              <p className="line-clamp-2">{n.message}</p>
              <p className="mt-0.5 text-[11px] text-muted-foreground">{formatDateTime(n.created_at)}</p>
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}

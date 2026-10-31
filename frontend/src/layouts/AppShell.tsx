import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Banknote,
  BarChart3,
  Bell,
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  Gavel,
  LayoutDashboard,
  LogOut,
  Moon,
  Scale,
  ScrollText,
  Sun,
  Theater,
  User as UserIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ClockControl } from "@/components/amanat/ClockControl";
import { NotificationBell } from "@/components/amanat/NotificationBell";
import { SimulatedBadge } from "@/components/amanat/SimulatedBadge";
import { useAuth } from "@/lib/AuthContext";
import { useTheme } from "@/lib/ThemeContext";
import { roleLabel } from "@/lib/roles";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["scrutiny", "senior_approver", "competent_authority", "admin"] },
  { to: "/queue", label: "Verification Queue", icon: Scale, roles: ["scrutiny", "senior_approver", "competent_authority"] },
  { to: "/flags", label: "Anomalies", icon: AlertTriangle, roles: ["scrutiny", "senior_approver", "competent_authority", "admin"] },
  { to: "/bank-requests", label: "Bank Requests", icon: Banknote, roles: ["scrutiny", "senior_approver", "competent_authority"] },
  { to: "/reminders", label: "Reminders", icon: Bell, roles: ["scrutiny", "senior_approver", "competent_authority", "admin"] },
  { to: "/releases", label: "Releases", icon: Gavel, roles: ["scrutiny", "senior_approver", "competent_authority", "institution"] },
  { to: "/rules", label: "Rules", icon: ScrollText, roles: ["admin"] },
  { to: "/audit", label: "Audit", icon: ScrollText, roles: ["auditor", "competent_authority"] },
  { to: "/metrics", label: "Metrics", icon: BarChart3, roles: ["scrutiny", "senior_approver", "competent_authority", "admin", "auditor"] },
  { to: "/demo", label: "Demo Scenarios", icon: Theater, roles: ["institution", "scrutiny", "senior_approver", "competent_authority", "admin", "auditor", "bank_officer"] },
];

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();

  const items = NAV_ITEMS.filter((item) => !user || item.roles.includes(user.role));

  return (
    <div className="flex min-h-screen bg-gradient-to-b from-slate-50 via-white to-indigo-50/40 dark:from-slate-950 dark:via-slate-900 dark:to-indigo-950/40">
      <aside
        className={cn(
          "flex flex-col border-r transition-all duration-200",
          collapsed ? "w-16" : "w-64",
        )}
      >
        <div className="brand-gradient flex items-center gap-2 px-4 py-5 text-white">
          <CalendarClock className="h-6 w-6 shrink-0" />
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate font-semibold tracking-tight">Amanat</p>
              <p className="truncate text-[10px] opacity-90">Every deposit covered, every claim checked, every date watched</p>
            </div>
          )}
        </div>
        <nav className="flex-1 space-y-1 p-2">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive ? "bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300" : "text-muted-foreground hover:bg-muted",
                )
              }
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </NavLink>
          ))}
        </nav>
        <Button variant="ghost" size="sm" className="mx-2 mb-2 justify-center" onClick={() => setCollapsed((v) => !v)}>
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
        <SimulatedBadge />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b bg-background/80 px-4 py-2.5 backdrop-blur">
          <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
            Amanat
          </Link>
          <div className="flex items-center gap-2">
            <ClockControl />
            <NotificationBell />
            <Button variant="ghost" size="icon" onClick={toggleTheme}>
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="gap-2">
                  <UserIcon className="h-4 w-4" />
                  <span className="hidden sm:inline">{user?.name}</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <div className="px-2 py-1.5 text-xs text-muted-foreground">{user ? roleLabel(user.role) : ""}</div>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => {
                    logout();
                    navigate("/login");
                  }}
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <motion.main
          key={location.pathname}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="flex-1 overflow-y-auto p-4 md:p-6"
        >
          <Outlet />
        </motion.main>
      </div>
    </div>
  );
}

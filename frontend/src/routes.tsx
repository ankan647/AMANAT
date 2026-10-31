import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/layouts/AppShell";
import { BankShell } from "@/layouts/BankShell";
import { PublicShell } from "@/layouts/PublicShell";
import { ProtectedRoute } from "@/lib/ProtectedRoute";
import { LoginPage } from "@/pages/Login";
import { DashboardPage } from "@/pages/Dashboard";
import { InstitutionDetailPage } from "@/pages/InstitutionDetail";
import { InstrumentDetailPage } from "@/pages/InstrumentDetail";
import { QueuePage } from "@/pages/Queue";
import { BankPortalPage } from "@/pages/BankPortal";
import { BankRequestsPage } from "@/pages/BankRequests";
import { FlagsPage } from "@/pages/Flags";
import { FlagDetailPage } from "@/pages/FlagDetail";
import { RulesPage } from "@/pages/Rules";
import { RemindersPage } from "@/pages/Reminders";
import { ReleasesPage } from "@/pages/Releases";
import { ReleaseDetailPage } from "@/pages/ReleaseDetail";
import { VerifyPage } from "@/pages/Verify";
import { AuditPage } from "@/pages/Audit";
import { MetricsPage } from "@/pages/Metrics";
import { DemoPage } from "@/pages/Demo";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route path="/verify/:orderNo" element={<PublicShell />}>
        <Route index element={<VerifyPage />} />
      </Route>
      <Route path="/verify" element={<PublicShell />}>
        <Route index element={<VerifyPage />} />
      </Route>

      <Route
        path="/bank"
        element={
          <ProtectedRoute allow={["bank_officer"]}>
            <BankShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<BankPortalPage />} />
      </Route>

      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="/queue" element={<QueuePage />} />
        <Route path="/institutions/:id" element={<InstitutionDetailPage />} />
        <Route path="/instruments/:id" element={<InstrumentDetailPage />} />
        <Route path="/bank-requests" element={<BankRequestsPage />} />
        <Route path="/flags" element={<FlagsPage />} />
        <Route path="/flags/:id" element={<FlagDetailPage />} />
        <Route path="/rules" element={<RulesPage />} />
        <Route path="/reminders" element={<RemindersPage />} />
        <Route path="/releases" element={<ReleasesPage />} />
        <Route path="/releases/:id" element={<ReleaseDetailPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/metrics" element={<MetricsPage />} />
        <Route path="/demo" element={<DemoPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

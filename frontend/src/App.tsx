import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/layout/Layout";
import { PrivateRoute } from "@/components/layout/PrivateRoute";
import { Toaster } from "@/components/ui/Toaster";
import { AuditPage } from "@/pages/AuditPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { RulesPage } from "@/pages/RulesPage";
import { ScanDetailsPage } from "@/pages/ScanDetailsPage";
import { ScansListPage } from "@/pages/ScansListPage";
import { UploadPage } from "@/pages/UploadPage";
import { UsersPage } from "@/pages/UsersPage";

export function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route path="/" element={<Navigate to="/scans" replace />} />
          <Route path="/scans" element={<ScansListPage />} />
          <Route path="/scans/:id" element={<ScanDetailsPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <Toaster />
    </>
  );
}

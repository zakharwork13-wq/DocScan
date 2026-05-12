import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/layout/Layout";
import { PrivateRoute } from "@/components/layout/PrivateRoute";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { ScanDetailsPage } from "@/pages/ScanDetailsPage";
import { ScansListPage } from "@/pages/ScansListPage";
import { UploadPage } from "@/pages/UploadPage";

export function App() {
  return (
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
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

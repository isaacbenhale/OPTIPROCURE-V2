import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { CallbackPage } from "./pages/CallbackPage";
import { LoginPage } from "./pages/LoginPage";
import { ReferenceDataPage } from "./pages/ReferenceDataPage";
import { SecurityPage } from "./pages/SecurityPage";
import { TenderCreatePage } from "./pages/TenderCreatePage";
import { TenderDetailPage } from "./pages/TenderDetailPage";
import { TendersListPage } from "./pages/TendersListPage";
import { UsersPage } from "./pages/UsersPage";

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="centered">
        <p>Chargement…</p>
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function RequireAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== "ADMIN") {
    return <Navigate to="/tenders" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/callback" element={<CallbackPage />} />
      <Route
        element={
          <RequireAuth>
            <Layout />
          </RequireAuth>
        }
      >
        <Route path="/" element={<Navigate to="/tenders" replace />} />
        <Route path="/tenders" element={<TendersListPage />} />
        <Route path="/tenders/new" element={<TenderCreatePage />} />
        <Route path="/tenders/:id" element={<TenderDetailPage />} />
        <Route
          path="/referentiels"
          element={
            <RequireAdmin>
              <ReferenceDataPage />
            </RequireAdmin>
          }
        />
        <Route
          path="/utilisateurs"
          element={
            <RequireAdmin>
              <UsersPage />
            </RequireAdmin>
          }
        />
        <Route path="/securite" element={<SecurityPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/tenders" replace />} />
    </Routes>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}

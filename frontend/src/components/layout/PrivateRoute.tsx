import { Navigate } from "react-router-dom";

import { useAuthStore } from "@/store/auth";

interface Props {
  children: React.ReactNode;
}

export function PrivateRoute({ children }: Props) {
  const accessToken = useAuthStore((s) => s.accessToken);

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

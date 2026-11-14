// UI route guards mirror the server's role checks (the server enforces them
// regardless — FR-LEN-07, SEC-06/07).
import type { ReactNode } from "react";
import { Navigate } from "react-router";

import type { Role } from "../api/types";
import { Loading } from "../components/PageShell";
import { useAuth } from "./Auth";

export function homeFor(role: Role): string {
  return role === "lender_officer" ? "/lender/cases" : "/profiles";
}

export function RequireRole({ role, children }: { role: Role; children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  if (!me) return <Navigate to="/login" replace />;
  if (me.role !== role) return <Navigate to={homeFor(me.role)} replace />;
  return <>{children}</>;
}

/** Welcome/login/register: a logged-in user goes straight to their home. */
export function GuestOnly({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Loading />;
  if (me) return <Navigate to={homeFor(me.role)} replace />;
  return <>{children}</>;
}

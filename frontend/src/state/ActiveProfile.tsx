// Active profile = the {pid} in the URL (shareable, reload-safe; TRD §3).
// On 404 (not owned / gone) the user is sent back to the chooser.
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router";

import { api, ApiError } from "../api/client";
import type { Profile } from "../api/types";

const ActiveProfileContext = createContext<Profile | null>(null);
const ReloadContext = createContext<() => Promise<void>>(async () => {});

export function ActiveProfileProvider({ children, fallback }: { children: ReactNode; fallback: ReactNode }) {
  const { pid } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<Profile | null>(null);

  useEffect(() => {
    let alive = true;
    setProfile(null);
    api<Profile>(`/profiles/${pid}`)
      .then((p) => alive && setProfile(p))
      .catch((e) => {
        if (alive && e instanceof ApiError && e.status === 404) void navigate("/profiles", { replace: true });
      });
    return () => {
      alive = false;
    };
  }, [pid, navigate]);

  /** Re-read the profile after a screen changed it (e.g. household money). */
  const reload = useCallback(async () => {
    setProfile(await api<Profile>(`/profiles/${pid}`));
  }, [pid]);

  if (!profile) return <>{fallback}</>;
  return (
    <ReloadContext.Provider value={reload}>
      <ActiveProfileContext.Provider value={profile}>{children}</ActiveProfileContext.Provider>
    </ReloadContext.Provider>
  );
}

export function useActiveProfile(): Profile {
  const p = useContext(ActiveProfileContext);
  if (!p) throw new Error("useActiveProfile outside ActiveProfileProvider");
  return p;
}

export function useReloadProfile(): () => Promise<void> {
  return useContext(ReloadContext);
}

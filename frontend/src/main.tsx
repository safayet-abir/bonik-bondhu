import "@fontsource/noto-sans-bengali/400.css";
import "@fontsource/noto-sans-bengali/600.css";
import "@fontsource/noto-sans/400.css";
import "@fontsource/noto-sans/600.css";
import "./styles/tokens.css";
import "./i18n";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router";

import { setSessionExpiredHandler } from "./api/client";
import { router } from "./router";
import { AuthProvider } from "./state/Auth";

// Any 401 SESSION_EXPIRED/AUTH_REQUIRED -> login with a message (FR-AUTH-06).
setSessionExpiredHandler(() => {
  const { pathname, search } = router.state.location; // FS-05: come back here after logging in
  void router.navigate("/login", { state: { reason: "auth.session_expired", from: pathname + search } });
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);

import { createBrowserRouter } from "react-router";

import { Login } from "./pages/auth/Login";
import { Register } from "./pages/auth/Register";
import { Welcome } from "./pages/auth/Welcome";
import { Cases } from "./pages/lender/Cases";
import { NotFound } from "./pages/NotFound";
import { AddEntry } from "./pages/owner/AddEntry";
import { Home } from "./pages/owner/Home";
import { More } from "./pages/owner/More";
import { OwnerLayout } from "./pages/owner/OwnerLayout";
import { ProfileCreate } from "./pages/owner/ProfileCreate";
import { Profiles } from "./pages/owner/Profiles";
import { Summary } from "./pages/owner/Summary";
import { GuestOnly, RequireRole } from "./state/Guards";

// Routes per TRD §3. Only screens with working endpoints exist (MP §17 rule 10);
// later phases add entries list, suppliers, debts, forecast, financing, etc.
export const router = createBrowserRouter([
  { path: "/", element: <GuestOnly><Welcome /></GuestOnly> },
  { path: "/register", element: <GuestOnly><Register /></GuestOnly> },
  { path: "/login", element: <Login /> },
  { path: "/profiles", element: <RequireRole role="owner"><Profiles /></RequireRole> },
  { path: "/profiles/new", element: <RequireRole role="owner"><ProfileCreate /></RequireRole> },
  {
    path: "/p/:pid",
    element: <RequireRole role="owner"><OwnerLayout /></RequireRole>,
    children: [
      { path: "home", element: <Home /> },
      { path: "entries/new", element: <AddEntry /> },
      { path: "summary", element: <Summary /> },
      { path: "more", element: <More /> },
    ],
  },
  { path: "/lender/cases", element: <RequireRole role="lender_officer"><Cases /></RequireRole> },
  { path: "*", element: <NotFound /> },
]);

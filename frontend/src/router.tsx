import { createBrowserRouter } from "react-router";

import { Login } from "./pages/auth/Login";
import { Register } from "./pages/auth/Register";
import { Welcome } from "./pages/auth/Welcome";
import { Harvest } from "./pages/farm/Harvest";
import { SeasonDetail } from "./pages/farm/SeasonDetail";
import { SeasonForm } from "./pages/farm/SeasonForm";
import { SeasonSummary } from "./pages/farm/SeasonSummary";
import { Cases } from "./pages/lender/Cases";
import { NotFound } from "./pages/NotFound";
import { AddEntry } from "./pages/owner/AddEntry";
import { Debts } from "./pages/owner/Debts";
import { Entries } from "./pages/owner/Entries";
import { EntryDetail } from "./pages/owner/EntryDetail";
import { ProfileHome } from "./pages/owner/Home";
import { More } from "./pages/owner/More";
import { OwnerLayout } from "./pages/owner/OwnerLayout";
import { ProfileCreate } from "./pages/owner/ProfileCreate";
import { Profiles } from "./pages/owner/Profiles";
import { Summary } from "./pages/owner/Summary";
import { Suppliers } from "./pages/owner/Suppliers";
import { GuestOnly, RequireRole } from "./state/Guards";

// Routes per TRD §3. Only screens with working endpoints exist (MP §17 rule 10);
// later phases add forecast, financing, assessment, sharing and advisor.
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
      { path: "home", element: <ProfileHome /> },
      { path: "entries", element: <Entries /> },
      { path: "entries/new", element: <AddEntry /> },
      { path: "entries/:tid", element: <EntryDetail /> },
      { path: "summary", element: <Summary /> },
      { path: "suppliers", element: <Suppliers /> },
      { path: "debts", element: <Debts /> },
      { path: "seasons/new", element: <SeasonForm /> },
      { path: "seasons/:sid", element: <SeasonDetail /> },
      { path: "seasons/:sid/edit", element: <SeasonForm /> },
      { path: "seasons/:sid/harvest", element: <Harvest /> },
      { path: "seasons/:sid/summary", element: <SeasonSummary /> },
      { path: "more", element: <More /> },
    ],
  },
  { path: "/lender/cases", element: <RequireRole role="lender_officer"><Cases /></RequireRole> },
  { path: "*", element: <NotFound /> },
]);

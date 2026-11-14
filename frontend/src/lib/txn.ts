// Display metadata for the 12 entry types (UI spec §3 icons, SCR-O04 groups).
// Accounting itself lives on the server (engine/accounting.py).
import {
  ArrowDownCircle, Banknote, CalendarCheck, ClipboardList, Home, Landmark, NotebookPen, Percent,
  PlusCircle, Receipt, ShoppingCart, Wallet, type LucideIcon,
} from "lucide-react";

import type { TxnType } from "../api/types";

export const TXN_ICON: Record<TxnType, LucideIcon> = {
  sale_cash: ArrowDownCircle,
  sale_credit: NotebookPen,
  receivable_collection: Banknote,
  purchase_cash: ShoppingCart,
  purchase_credit: ClipboardList,
  payable_payment: Wallet,
  operating_expense: Receipt,
  loan_received: Landmark,
  loan_principal_repayment: CalendarCheck,
  loan_interest_fee_payment: Percent,
  owner_withdrawal: Home,
  owner_contribution: PlusCircle,
};

/** SCR-O04 type picker, grouped so 12 buttons stay readable on 360 px. */
export const TXN_GROUPS: { key: string; types: TxnType[] }[] = [
  { key: "sales", types: ["sale_cash", "sale_credit", "receivable_collection"] },
  { key: "buying", types: ["purchase_cash", "purchase_credit", "payable_payment", "operating_expense"] },
  { key: "loans", types: ["loan_received", "loan_principal_repayment", "loan_interest_fee_payment"] },
  { key: "owner", types: ["owner_withdrawal", "owner_contribution"] },
];

export const SUPPLIER_TYPES: TxnType[] = ["purchase_cash", "purchase_credit", "payable_payment"];
export const LOAN_TYPES: TxnType[] = ["loan_received", "loan_principal_repayment", "loan_interest_fee_payment"];
/** Types that can pay for a planned season cost item (server rule). */
export const COST_ITEM_TYPES: TxnType[] = ["purchase_cash", "purchase_credit", "payable_payment", "operating_expense"];

/** Cash moves in / out / not cash (baki). Used only for colour + sign. */
export function cashDirection(t: TxnType): "in" | "out" | "none" {
  if (t === "sale_credit" || t === "purchase_credit") return "none";
  if (["sale_cash", "receivable_collection", "loan_received", "owner_contribution"].includes(t)) return "in";
  return "out";
}

/** SCR-O06 filter chips → server txn_type filter. */
export const LIST_FILTERS: Record<string, { types?: TxnType[]; status?: "voided" }> = {
  all: {},
  in: { types: ["sale_cash", "sale_credit", "receivable_collection", "owner_contribution"] },
  out: { types: ["purchase_cash", "purchase_credit", "payable_payment", "operating_expense", "owner_withdrawal"] },
  loans: { types: LOAN_TYPES },
  voided: { status: "voided" },
};

export const SHOP_EXPENSE_CATEGORIES = ["rent", "salary", "utility", "transport", "other"];
export const FARM_COST_CATEGORIES = [
  "seed", "fertilizer", "pesticide", "irrigation", "labour", "land_lease", "transport", "other",
];

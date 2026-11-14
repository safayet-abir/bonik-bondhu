import { useState, type ChangeEvent } from "react";

import { normalizeDigits } from "../lib/format";
import { Field } from "./Field";

type Props = {
  label: string;
  /** Normalised value: Latin digits, no commas, e.g. "8500" or "8500.5". */
  value: string;
  onChange: (normalised: string) => void;
  hint?: string;
  errorKey?: string;
  name?: string;
};

const PARTIAL_AMOUNT = /^\d*(\.\d{0,2})?$/;

/** Taka amount input: accepts Bangla (০-৯) or Latin digits and commas,
 *  at most 2 decimals (UI spec §7.1). The server re-validates. */
export function AmountInput({ label, value, onChange, hint, errorKey, name }: Props) {
  const [raw, setRaw] = useState(value);

  function handle(e: ChangeEvent<HTMLInputElement>) {
    const typed = e.target.value;
    const normalised = normalizeDigits(typed);
    if (!PARTIAL_AMOUNT.test(normalised)) return; // ignore invalid keystroke
    setRaw(typed);
    onChange(normalised);
  }

  return (
    <Field
      label={label}
      name={name}
      value={raw}
      onChange={handle}
      inputMode="decimal"
      autoComplete="off"
      hint={hint}
      errorKey={errorKey}
      className="tabular"
    />
  );
}

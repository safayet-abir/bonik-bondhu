import { Leaf, MapPin, Newspaper, Store, Truck, type LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";

import type { Lang } from "../i18n";
import { toBanglaDigits } from "../lib/format";
import { IconTile, type Tone } from "./Brand";

/** Plan Ultra F4 supply graph: business → suppliers → areas / goods → news (SVG + CSS, no chart library).
 *  The SVG is the picture; the button list under it is the accessible, keyboard-usable way to pick a node. */

export type GKind = "business" | "supplier" | "area" | "good" | "news";
export type GNode = {
  id: string; kind: GKind; label: string; exposure_pct: string | null;
  is_demo?: boolean; source_name?: string; published_date?: string; corroboration?: string; auto_collected?: boolean;
};
export type SupplyGraphData = {
  as_of: string; basis: string; window_days: number; whatif_available: boolean;
  nodes: GNode[]; edges: { from: string; to: string; relation: string }[];
};

export const KIND: Record<GKind, { tone: Tone; icon: LucideIcon }> = {
  business: { tone: "teal", icon: Store },
  supplier: { tone: "sky", icon: Truck },
  area: { tone: "turmeric", icon: MapPin },
  good: { tone: "leaf", icon: Leaf },
  news: { tone: "chili", icon: Newspaper },
};
// SVG fills per kind (same pairs as the icon tiles)
const FILL: Record<GKind, string> = {
  business: "fill-tile-teal", supplier: "fill-tile-sky", area: "fill-tile-turmeric", good: "fill-tile-leaf", news: "fill-tile-chili",
};
const INK: Record<GKind, string> = {
  business: "fill-tile-teal-ink", supplier: "fill-tile-sky-ink", area: "fill-tile-turmeric-ink", good: "fill-tile-leaf-ink",
  news: "fill-tile-chili-ink",
};
const COL: Record<GKind, number> = { business: 0, supplier: 1, area: 2, good: 2, news: 3 };
const X = [12, 200, 400, 588];
const NW = 172;
const NH = 46;
const GAP = 12;

export function pctText(p: string | null, lang: Lang): string {
  if (p === null) return "?";
  const v = p.replace(/\.0$/, "");
  return `${lang === "bn" ? toBanglaDigits(v) : v}%`;
}

function short(s: string, n = 22): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

export function GraphView({ g, selected, onSelect }: {
  g: SupplyGraphData; selected: string | null; onSelect?: (id: string) => void;
}) {
  const { i18n } = useTranslation();
  const lang = i18n.language as Lang;
  const cols: GNode[][] = [[], [], [], []];
  for (const kind of ["business", "supplier", "area", "good", "news"] as GKind[]) {
    for (const n of g.nodes) if (n.kind === kind) cols[COL[kind]].push(n);
  }
  // the picture keeps the 6 news items that touch the most purchases; the list below shows every one
  cols[3] = [...cols[3]].sort((a, b) => Number(b.exposure_pct ?? -1) - Number(a.exposure_pct ?? -1)).slice(0, 6);
  const rows = Math.max(1, ...cols.map((c) => c.length));
  const H = 24 + rows * (NH + GAP);
  const pos = new Map<string, { x: number; y: number; col: number }>();
  cols.forEach((c, ci) => {
    const top = (H - c.length * (NH + GAP) + GAP) / 2;
    c.forEach((n, i) => pos.set(n.id, { x: X[ci], y: top + i * (NH + GAP), col: ci }));
  });
  const near = new Set<string>(selected ? [selected] : []);
  if (selected) for (const e of g.edges) if (e.from === selected || e.to === selected) { near.add(e.from); near.add(e.to); }
  const dim = (id: string) => (selected && !near.has(id) ? 0.3 : 1);

  return (
    <svg viewBox={`0 0 772 ${H}`} className="block w-full min-w-[680px]" aria-hidden>
      {g.edges.map((e) => {
        const a = pos.get(e.from);
        const b = pos.get(e.to);
        if (!a || !b) return null;
        const [l, r] = a.col <= b.col ? [a, b] : [b, a];
        const x1 = l.x + NW, y1 = l.y + NH / 2, x2 = r.x, y2 = r.y + NH / 2, mx = (x1 + x2) / 2;
        const on = selected !== null && (e.from === selected || e.to === selected);
        return (
          <path key={`${e.from}>${e.to}>${e.relation}`} d={`M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`} fill="none"
                className={on ? "stroke-bb-iron" : "stroke-bb-muted"} strokeWidth={on ? 2.5 : 1.2}
                strokeDasharray={e.relation === "affects" ? "5 4" : undefined} opacity={selected && !on ? 0.2 : 0.7} />
        );
      })}
      {g.nodes.filter((n) => pos.has(n.id)).map((n) => {
        const p = pos.get(n.id)!;
        const sel = n.id === selected;
        return (
          <g key={n.id} transform={`translate(${p.x} ${p.y})`} opacity={dim(n.id)} onClick={() => onSelect?.(n.id)}
             className={onSelect ? "cursor-pointer" : ""}>
            <rect x={3} y={3} width={NW} height={NH} rx={10} className="fill-bb-iron" />
            <rect width={NW} height={NH} rx={10} className={`${FILL[n.kind]} stroke-bb-iron`} strokeWidth={sel ? 3 : 2} />
            <text x={10} y={19} className={`${INK[n.kind]} font-display`} fontSize={13} fontWeight={600}>{short(n.label)}</text>
            {n.kind !== "business" ? (
              <text x={10} y={36} className="fill-bb-iron" fontSize={12}>{pctText(n.exposure_pct, lang)}</text>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
}

/** The accessible picker: every node as a button, grouped by kind, with its exposure. */
export function NodeList({ g, selected, onSelect }: { g: SupplyGraphData; selected: string | null; onSelect: (id: string) => void }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language as Lang;
  return (
    <div className="flex flex-col gap-3">
      {(["area", "good", "supplier", "news"] as GKind[]).map((kind) => {
        const items = g.nodes.filter((n) => n.kind === kind);
        if (items.length === 0) return null;
        return (
          <section key={kind} className="flex flex-col gap-2">
            <h3 className="flex items-center gap-2 font-semibold">
              <IconTile icon={KIND[kind].icon} tone={KIND[kind].tone} size="sm" />{t(`graph.kind.${kind}`)}
            </h3>
            <ul className="flex flex-wrap gap-2">
              {items.map((n) => (
                <li key={n.id}>
                  <button type="button" aria-pressed={n.id === selected} onClick={() => onSelect(n.id)}
                          className={`flex min-h-11 items-center gap-2 rounded-xl px-3 text-left text-small transition-transform duration-100 active:translate-y-px ${
                            n.id === selected ? "bb-hard-sm bg-bb-brass font-semibold text-bb-iron" : "border-2 border-bb-border bg-bb-surface"}`}>
                    <span className="max-w-[16rem] truncate">{n.label}</span>
                    <span className="tabular font-semibold">{pctText(n.exposure_pct, lang)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

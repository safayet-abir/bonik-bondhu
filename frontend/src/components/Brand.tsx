import type { LucideIcon } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import credits from "../data/photo-credits.json";

/** Brand pieces shared by every screen (design round 3): the logo, the bazaar photos with their credit,
 *  and the coloured icon tile. Photos are self-hosted (CSP img-src 'self'); licences in public/photos/CREDITS.md. */

export type PhotoSlug = keyof typeof credits;
export type Tone = "chili" | "turmeric" | "leaf" | "sky" | "plum" | "teal";

/** The mark (public/brand/logo-mark.svg — the same file the posters use) + the Bangla/English wordmark. */
export function Logo({ tone = "wall", to, className = "" }: { tone?: "wall" | "light"; to?: string; className?: string }) {
  const body = (
    <>
      <img src="/brand/logo-mark.svg" alt="" className="size-10 shrink-0" />
      <span className="flex flex-col leading-none">
        <span lang="bn" className={`font-display text-[1.35rem] font-semibold ${tone === "wall" ? "text-white" : "text-bb-iron"}`}>
          বণিক বন্ধু
        </span>
        <span lang="en" className={`mt-1 text-[0.62rem] font-semibold tracking-[0.24em] ${tone === "wall" ? "text-bb-brass" : "text-bb-primary"}`}>
          BONIK BONDHU
        </span>
      </span>
    </>
  );
  const cls = `inline-flex min-h-12 items-center gap-2.5 ${className}`;
  return to ? <Link to={to} className={cls} aria-label="বণিক বন্ধু · Bonik Bondhu">{body}</Link>
            : <span className={cls}>{body}</span>;
}

/** A bazaar/field photo: 800 px for phones, 1600 px for wide screens. `alt=""` when it is only a backdrop. */
export function Photo({ slug, decorative, className = "", drift }: {
  slug: PhotoSlug; decorative?: boolean; className?: string; drift?: boolean;
}) {
  const { t } = useTranslation();
  return (
    <img src={`/photos/${slug}-800.webp`} srcSet={`/photos/${slug}-800.webp 800w, /photos/${slug}-1600.webp 1600w`}
         sizes="(min-width: 1024px) 50vw, 100vw" alt={decorative ? "" : t(`photo.${slug}`)}
         loading="lazy" decoding="async" className={`size-full object-cover ${drift ? "bb-drift" : ""} ${className}`} />
  );
}

/** The CC credit for a photo, linking to its Commons page. */
export function PhotoCredit({ slug, className = "" }: { slug: PhotoSlug; className?: string }) {
  const { t } = useTranslation();
  const c = credits[slug];
  return (
    <a href={c.source} target="_blank" rel="noopener noreferrer" className={`text-caption underline-offset-2 hover:underline ${className}`}>
      {t("brand.photo_by", { author: c.author, licence: c.licence })}
    </a>
  );
}

export const TONES: Record<Tone, string> = {
  chili: "bg-tile-chili text-tile-chili-ink",
  turmeric: "bg-tile-turmeric text-tile-turmeric-ink",
  leaf: "bg-tile-leaf text-tile-leaf-ink",
  sky: "bg-tile-sky text-tile-sky-ink",
  plum: "bg-tile-plum text-tile-plum-ink",
  teal: "bg-tile-teal text-tile-teal-ink",
};

/** A coloured icon tile with the iron edge — always next to a text label, never alone (UI spec §1.4). */
export function IconTile({ icon: Icon, tone, size = "md", className = "" }: {
  icon: LucideIcon; tone: Tone; size?: "sm" | "md" | "lg"; className?: string;
}) {
  const box = size === "sm" ? "size-8 rounded-md" : size === "lg" ? "size-14 rounded-xl" : "size-11 rounded-lg";
  const ico = size === "sm" ? "size-4" : size === "lg" ? "size-7" : "size-5";
  return (
    <span aria-hidden className={`bb-hard-sm inline-flex shrink-0 items-center justify-center ${box} ${TONES[tone]} ${className}`}>
      <Icon className={ico} strokeWidth={2.2} />
    </span>
  );
}

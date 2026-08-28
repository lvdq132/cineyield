"use client";

import Link from "next/link";
import type { ContentProject, LibraryStat } from "@/lib/types";
import { StatusBadge } from "@/components/ui";
import { useAppState } from "@/context/AppStateContext";
import { DEMO_ESTIMATED_VALUE, getLibraryStats } from "@/data/content";
import { PrimaryButton, SecondaryButton } from "@/components/ui";
import { DataSourceNotice } from "@/components/ui/DataSourceNotice";
import type { DataSource } from "@/lib/data-source";

interface LibraryViewProps {
  catalog: ContentProject[];
  /** Real ClickHouse-derived stats. Omitted in fixture mode, where the demo constants stand in. */
  stats?: LibraryStat[];
  /** Real approved revenue. Omitted in fixture mode. */
  approvedRevenue?: string;
  dataSource?: DataSource;
}

export function LibraryView({
  catalog,
  stats: liveStats,
  approvedRevenue,
  dataSource = "live",
}: LibraryViewProps) {
  const { approved, startAnalyze } = useAppState();
  const stats = liveStats ?? getLibraryStats(approved);

  return (
    <div className="animate-cyrise">
      <section className="relative mb-14 min-h-[590px] overflow-hidden border-b border-line">
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(9,10,11,.96)_0%,rgba(9,10,11,.80)_46%,rgba(9,10,11,.25)_100%),linear-gradient(0deg,#090a0b_0%,transparent_48%),url('/cineyield-rooftop-hero.jpg')] bg-cover bg-center" />
        <div className="relative grid min-h-[590px] grid-cols-1 content-between gap-12 px-[clamp(24px,4vw,64px)] py-[clamp(54px,7vw,92px)] lg:grid-cols-[1.1fr_.9fr]">
          <div className="lg:col-span-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-[0.14em] text-gold">Studio inventory / Live workspace</span>
          </div>
          <div className="self-end">
            <h1 className="m-0 max-w-[820px] text-[clamp(58px,7vw,108px)] font-medium leading-[0.84] tracking-[-0.07em] text-ink">
              Find the value<br />inside the cut.
            </h1>
          </div>
          <div className="self-end lg:pb-1">
            <p className="m-0 max-w-[560px] text-[18px] leading-[1.58] text-ink2">
              Analyze finished footage, qualify sponsor demand, and prepare a producer-controlled decision with every source and constraint visible.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
            <PrimaryButton onClick={startAnalyze}>
              Analyze a Cut
              <span aria-hidden>↗</span>
            </PrimaryButton>
            <SecondaryButton href="/marketplace">
              Browse Demand
              <span aria-hidden>→</span>
            </SecondaryButton>
          </div>
        </div>
        </div>
      </section>

      <div className="mx-auto max-w-[1100px]">
        <DataSourceNotice source={dataSource} />
      </div>

      <div className="mx-auto mb-20 mt-2 grid max-w-[1100px] grid-cols-2 border-y border-line md:grid-cols-5">
        <div className="min-h-[118px] border-b border-r border-line p-5 md:border-b-0">
          <div className="text-[32px] font-semibold leading-none tracking-[-0.04em] text-gold">
            {approvedRevenue ?? DEMO_ESTIMATED_VALUE}
          </div>
          <div className="mt-8 text-[10px] font-bold uppercase tracking-[0.08em] text-ink3">
            {approvedRevenue ? "Approved revenue" : "Estimated value"}
          </div>
        </div>
        {stats.map((stat, index) => (
          <div key={stat.label} className={`min-h-[118px] border-line p-5 ${index % 2 === 0 ? "border-r" : ""} md:border-r md:last:border-r-0`}>
            <div
              className={`text-[32px] font-semibold leading-none tracking-[-0.04em] ${
                stat.color === "amber" ? "text-amber" : "text-ink"
              }`}
            >
              {stat.value}
            </div>
            <div className="mt-8 text-[10px] font-bold uppercase tracking-[0.08em] text-ink3">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="mb-9 flex flex-wrap items-end justify-between gap-5 border-b border-line pb-5">
        <div>
          <span className="font-mono text-[9px] font-bold uppercase tracking-[0.12em] text-gold">Catalog / Sponsor-ready inventory</span>
          <h2 className="mt-4 text-[clamp(42px,5vw,72px)] font-medium leading-[0.9] tracking-[-0.06em] text-ink">Analyzed titles.</h2>
        </div>
        <p className="max-w-[470px] text-[15px] leading-[1.6] text-ink2">Every title shows analyzed coverage, qualified opportunities, and modeled value without hiding incomplete work.</p>
      </div>

      <div className="grid grid-cols-1 border-l border-t border-line md:grid-cols-2 lg:grid-cols-3">
        {catalog.map((item) => (
          <ContentCard key={item.id} item={item} />
        ))}
      </div>
    </div>
  );
}

function ContentCard({ item }: { item: ContentProject }) {
  // A card is only a link if the asset actually has an analyzed scene to open.
  // Previously every card pointed at one hardcoded scene, so any title a judge
  // clicked landed on the same page.
  const body = <ContentCardBody item={item} />;
  if (!item.href) {
    return (
      <div
        className="overflow-hidden border-b border-r border-line bg-panel opacity-70"
        title="No analyzed scenes yet"
        aria-disabled="true"
      >
        {body}
      </div>
    );
  }
  return (
    <Link
      href={item.href}
      className="cursor-pointer overflow-hidden border-b border-r border-line bg-panel transition-colors hover:bg-panel2"
    >
      {body}
    </Link>
  );
}

function ContentCardBody({ item }: { item: ContentProject }) {
  return (
    <>
      <div
        className="relative h-[190px]"
        style={{ background: item.thumbnailGradient }}
      >
        <StatusBadge status={item.status} />
        <span className="absolute bottom-3 left-3.5 text-[11px] text-[rgba(255,255,255,0.66)]">
          {item.format}
        </span>
      </div>
      <div className="px-4 pb-[18px] pt-4">
        <div className="flex items-baseline justify-between gap-2.5">
          <div className="text-[21px] font-bold leading-[1.1] tracking-[-0.02em] text-ink">
            {item.title}
          </div>
          <div className="flex-none text-[11px] text-ink3">{item.updated}</div>
        </div>
        <div className="mt-0.5 text-[12.5px] text-ink3">{item.subtitle}</div>
        <div className="mt-4 flex items-baseline gap-2">
          <span className="text-[12.5px] text-ink2">
            {item.analyzedScenes !== undefined && item.totalScenes !== undefined
              ? `${item.analyzedScenes}/${item.totalScenes} scenes analyzed`
              : `${item.scenes} scenes`}{" "}
            · {item.opportunities} opps
          </span>
          <span className="ml-auto text-[15px] font-semibold tracking-[-0.3px] text-gold">
            {item.estimatedValue}
          </span>
        </div>
      </div>
    </>
  );
}

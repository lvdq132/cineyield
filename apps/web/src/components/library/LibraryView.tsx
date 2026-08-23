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
      <section className="relative px-0 pb-10 pt-14 text-center">
        <div className="pointer-events-none absolute left-1/2 top-0 h-[400px] w-[860px] -translate-x-1/2 bg-[radial-gradient(46%_52%_at_50%_36%,rgba(59,130,246,0.22),transparent_70%)]" />
        <div className="relative mx-auto max-w-[760px]">
          <div className="mb-[26px] inline-flex h-[30px] items-center gap-2 rounded-full border border-line2 bg-panel px-3.5 text-[12.5px] text-ink2">
            <span className="h-1.5 w-1.5 rounded-full bg-gold shadow-[0_0_8px_var(--color-gold)]" />
            Introducing Scene Intelligence
            <span className="text-ink3">→</span>
          </div>
          <h1 className="m-0 text-[64px] font-bold leading-[0.98] tracking-[-0.035em] text-ink">
            Every scene, read as
            <br />
            sellable inventory
          </h1>
          <p className="mx-auto mt-[22px] max-w-[560px] text-[16px] leading-[1.55] text-ink2">
            AI scene understanding, rights clearance, and brand matching — built on
            Gemini, ClickHouse, and deterministic guardrails. Your catalog, monetized.
          </p>
          <div className="mt-8 flex justify-center gap-3">
            <PrimaryButton onClick={startAnalyze}>
              Analyze a Cut
              <span className="text-[17px] opacity-70">›</span>
            </PrimaryButton>
            <SecondaryButton href="/marketplace">
              Browse Catalog
              <span className="text-[17px] opacity-55">›</span>
            </SecondaryButton>
          </div>
          <div className="mt-[42px] flex flex-wrap items-center justify-center gap-[18px] text-[12.5px] font-medium text-ink3">
            <span>Gemini</span>
            <span className="opacity-35">/</span>
            <span>ClickHouse</span>
            <span className="opacity-35">/</span>
            <span>MCP</span>
            <span className="opacity-35">/</span>
            <span>Cloud Storage</span>
            <span className="opacity-35">/</span>
            <span>Vertex AI</span>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-[880px]">
        <DataSourceNotice source={dataSource} />
      </div>

      <div className="mx-auto mb-16 mt-2 flex max-w-[880px] flex-wrap justify-center gap-x-[72px] gap-y-[18px] border-y border-line py-[30px]">
        <div className="flex-none text-center">
          <div className="text-[28px] font-bold tracking-[-0.02em] text-gold">
            {approvedRevenue ?? DEMO_ESTIMATED_VALUE}
          </div>
          <div className="mt-1 text-[12px] text-ink3">
            {approvedRevenue ? "Approved revenue" : "Estimated value"}
          </div>
        </div>
        {stats.map((stat) => (
          <div key={stat.label} className="flex-none text-center">
            <div
              className={`text-[28px] font-bold tracking-[-0.02em] ${
                stat.color === "amber" ? "text-amber" : "text-ink"
              }`}
            >
              {stat.value}
            </div>
            <div className="mt-1 text-[12px] text-ink3">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="mb-1.5 text-center">
        <h2 className="m-0 text-[40px] font-bold tracking-[-0.03em] text-ink">
          Showcase
        </h2>
      </div>
      <p className="mb-9 text-center text-[15px] text-ink2">
        Studios use CineYield to turn their catalog into inventory.
      </p>

      <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
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
        className="overflow-hidden rounded-[10px] bg-panel opacity-70"
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
      className="cursor-pointer overflow-hidden rounded-[10px] bg-panel transition-colors hover:bg-panel2"
    >
      {body}
    </Link>
  );
}

function ContentCardBody({ item }: { item: ContentProject }) {
  return (
    <>
      <div
        className="relative h-[158px]"
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

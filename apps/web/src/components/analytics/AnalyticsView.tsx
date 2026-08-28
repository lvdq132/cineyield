"use client";

import type { AnalyticsStat, CategorySegment, ContentRevenue, TopScene } from "@/lib/types";
import { useAppState } from "@/context/AppStateContext";
import {
  getAnalyticsStats,
  demoCategorySegments,
  demoContentRevenue,
  demoTopScenes,
} from "@/data/analytics";
import { ProgressBar } from "@/components/ui";
import { DataSourceNotice } from "@/components/ui/DataSourceNotice";
import type { DataSource } from "@/lib/data-source";

interface AnalyticsViewProps {
  liveStats?: AnalyticsStat[];
  dataSource?: DataSource;
  /** Revenue-by-content-type rows derived from GET /content. Undefined => fall back to the fixture, marked illustrative. */
  liveContentRevenue?: ContentRevenue[];
  /** Category-mix donut segments derived from live opportunity data. Undefined => fall back to the fixture, marked illustrative. */
  liveCategorySegments?: CategorySegment[];
  /** Top-scenes rows derived from live opportunity data. Undefined => fall back to the fixture, marked illustrative. */
  liveTopScenes?: TopScene[];
}

export function AnalyticsView({
  liveStats,
  dataSource = "live",
  liveContentRevenue,
  liveCategorySegments,
  liveTopScenes,
}: AnalyticsViewProps) {
  const { approved } = useAppState();
  const stats = liveStats ?? getAnalyticsStats(approved);

  const contentRevenue = liveContentRevenue ?? demoContentRevenue;
  const contentRevenueModelled = !liveContentRevenue;
  const categorySegments = liveCategorySegments ?? demoCategorySegments;
  const categorySegmentsModelled = !liveCategorySegments;
  const topScenes = liveTopScenes ?? demoTopScenes;
  const topScenesModelled = !liveTopScenes;

  return (
    <div className="animate-cyrise">
      <div className="mb-8 grid grid-cols-1 gap-5 border-b border-line pb-7 md:grid-cols-[1fr_420px] md:items-end">
        <div><span className="font-mono text-[9px] font-bold uppercase tracking-[0.12em] text-gold">Portfolio intelligence / Outcomes</span><h1 className="mt-4 text-[clamp(42px,5vw,72px)] font-medium leading-[0.9] tracking-[-0.06em] text-ink">
          Analytics &amp; revenue.
        </h1></div>
        <p className="m-0 text-[15px] leading-[1.6] text-ink2">
          Outcomes read from persisted event data.{" "}
          <span className="text-ink3">{liveStats ? "Live ClickHouse data." : "Demo dataset."}</span>
        </p>
      </div>

      <DataSourceNotice source={dataSource} />

      <StatsGrid stats={stats} />

      {/* The revenue-over-time chart has no backing time-series source and
          is always illustrative, so this note always applies to at least
          one panel below — no need to gate it on stats. */}
      <div className="-mt-[8px] mb-[18px] rounded bg-well px-[13px] py-[11px] text-[11.5px] text-ink2">
        ⓘ Figures and panels marked <sup className="text-ink3">†</sup> are
        modelled projections or illustrative estimates, not computed from
        live event data.
      </div>

      <div className="mb-[18px] grid grid-cols-1 gap-[18px] lg:grid-cols-[1.5fr_1fr]">
        <RevenueChart />
        <CategoryDonut segments={categorySegments} modelled={categorySegmentsModelled} />
      </div>

      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-2">
        <ContentRevenuePanel data={contentRevenue} modelled={contentRevenueModelled} />
        <TopScenesPanel scenes={topScenes} modelled={topScenesModelled} />
      </div>
    </div>
  );
}

function StatsGrid({ stats }: { stats: AnalyticsStat[] }) {
  const colorMap = {
    ink: "text-ink",
    gold: "text-gold",
    green: "text-green",
    amber: "text-amber",
  };

  return (
    <div className="mb-[22px] grid grid-cols-2 border-t border-line sm:grid-cols-4">
      {stats.map((stat, i) => (
        <div
          key={stat.label}
          className={`py-5 pr-7 ${i > 3 ? "border-t border-line" : ""}`}
        >
          <div className="text-xs text-ink3">
            {stat.label}
            {stat.modelled && <sup className="ml-0.5 text-ink3">†</sup>}
          </div>
          <div
            className={`mt-2 text-[25px] font-semibold leading-none tracking-[-0.5px] ${
              colorMap[stat.color ?? "ink"]
            }`}
          >
            {stat.value}
          </div>
        </div>
      ))}
    </div>
  );
}

function RevenueChart() {
  return (
    <div className="rounded bg-panel p-[22px]">
      <div className="text-[19px] font-bold tracking-[-0.02em] text-ink">
        Approved placement value over time
        <sup className="ml-0.5 text-ink3">†</sup>
      </div>
      <div className="mb-[18px] mt-1 font-mono text-[11px] text-ink3">
        USD · trailing 6 months · illustrative, no time-series backend yet
      </div>
      <svg viewBox="0 0 560 200" className="h-auto w-full" role="img" aria-label="Revenue trend chart">
        <defs>
          <linearGradient id="cyfill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#f15d3b" stopOpacity="0.18" />
            <stop offset="1" stopColor="#f15d3b" stopOpacity="0" />
          </linearGradient>
        </defs>
        <line x1="40" y1="20" x2="40" y2="170" stroke="#1E1E22" />
        <line x1="40" y1="170" x2="540" y2="170" stroke="#1E1E22" />
        <path
          d="M40 150 L140 128 L240 132 L340 92 L440 70 L540 40 L540 170 L40 170 Z"
          fill="url(#cyfill)"
        />
        <path
          d="M40 150 L140 128 L240 132 L340 92 L440 70 L540 40"
          fill="none"
          stroke="#f15d3b"
          strokeWidth="2"
        />
        <circle cx="540" cy="40" r="3.5" fill="#ff7657" />
        {[
          { x: 40, label: "Mar" },
          { x: 140, label: "Apr" },
          { x: 240, label: "May" },
          { x: 340, label: "Jun" },
          { x: 440, label: "Jul" },
          { x: 520, label: "Aug" },
        ].map(({ x, label }) => (
          <text
            key={label}
            x={x}
            y="188"
            fill="#65656E"
            fontSize="10"
            fontFamily="Space Mono, monospace"
          >
            {label}
          </text>
        ))}
      </svg>
    </div>
  );
}

function CategoryDonut({ segments, modelled }: { segments: CategorySegment[]; modelled: boolean }) {
  // Cumulative-offset donut segments, css-tricks-style: each arc's dashoffset
  // is 25 minus the running total of pct already placed before it.
  let cumulative = 0;
  const arcs = segments.map((s) => {
    const dashoffset = 25 - cumulative;
    cumulative += s.pct;
    return { ...s, dashoffset };
  });

  return (
    <div className="rounded bg-panel p-[22px]">
      <div className="mb-[18px] text-[19px] font-bold tracking-[-0.02em] text-ink">
        Revenue by category
        {modelled && <sup className="ml-0.5 text-ink3">†</sup>}
      </div>
      <div className="flex items-center gap-[22px]">
        <svg width="120" height="120" viewBox="0 0 42 42" aria-hidden>
          <circle cx="21" cy="21" r="15.9" fill="none" stroke="#1E1E22" strokeWidth="6" />
          {arcs.map((s) => (
            <circle
              key={s.label}
              cx="21"
              cy="21"
              r="15.9"
              fill="none"
              stroke={s.color}
              strokeWidth="6"
              strokeDasharray={`${s.pct} ${100 - s.pct}`}
              strokeDashoffset={s.dashoffset}
              transform="rotate(-90 21 21)"
            />
          ))}
        </svg>
        <div className="flex flex-1 flex-col gap-2.5">
          {arcs.map((s) => (
            <div key={s.label} className="flex items-center gap-2 text-xs">
              <span className="h-2 w-2" style={{ background: s.color }} />
              <span className="flex-1 text-ink">{s.label}</span>
              <span className="font-mono text-xs text-ink2">{s.pct}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ContentRevenuePanel({ data, modelled }: { data: ContentRevenue[]; modelled: boolean }) {
  return (
    <div className="rounded bg-panel p-[22px]">
      <div className="mb-[18px] text-[19px] font-bold tracking-[-0.02em] text-ink">
        Revenue by content type
        {modelled && <sup className="ml-0.5 text-ink3">†</sup>}
      </div>
      <div className="flex flex-col gap-[15px]">
        {data.map((row) => (
          <div key={row.key}>
            <div className="mb-[7px] flex justify-between text-xs">
              <span className="text-ink">{row.key}</span>
              <span className="font-mono text-xs text-ink2">{row.value}</span>
            </div>
            <ProgressBar percent={row.percent} height="4px" />
          </div>
        ))}
      </div>
    </div>
  );
}

function TopScenesPanel({ scenes, modelled }: { scenes: TopScene[]; modelled: boolean }) {
  return (
    <div className="rounded bg-panel p-[22px]">
      <div className="mb-2 text-[19px] font-bold tracking-[-0.02em] text-ink">
        Top performing scenes
        {modelled && <sup className="ml-0.5 text-ink3">†</sup>}
      </div>
      {scenes.map((scene) => (
        <div
          key={scene.name}
          className="flex items-center gap-[13px] border-t border-line py-[11px]"
        >
          <div
            className="h-7 w-11 flex-none"
            style={{ background: scene.thumbGradient }}
          />
          <div className="flex-1">
            <div className="text-[13px] font-medium text-ink">{scene.name}</div>
            <div className="text-[11px] text-ink3">{scene.show}</div>
          </div>
          <div
            className={`font-mono text-sm font-bold ${
              scene.gold ? "text-gold" : "text-ink"
            }`}
          >
            {scene.value}
          </div>
        </div>
      ))}
    </div>
  );
}

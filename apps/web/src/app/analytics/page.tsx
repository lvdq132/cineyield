import { AnalyticsView } from "@/components/analytics/AnalyticsView";
import type { AnalyticsStat, CategorySegment, ContentRevenue, TopScene } from "@/lib/types";

import { IS_CONTEST_MODE as CONTEST_MODE } from "@/lib/contest-mode";
import { dataSourceFor } from "@/lib/data-source";
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

const FORMAT_LABELS: Record<string, string> = {
  tv_series: "TV Series",
  film: "Feature Film",
  youtube: "YouTube / Creator",
  microdrama: "Microdrama",
  social: "Social",
};

// Same 4-shade palette CategoryDonut always used — the 4th slot is an
// aggregate "Other" bucket whenever more than 3 real categories exist, so
// the chart still reads as exactly 4 segments.
const CATEGORY_COLORS = ["#f15d3b", "#d94c2e", "#a83f2a", "#6f3327"];

const SCENE_GRADIENTS = [
  "radial-gradient(circle at 40% 30%,#3a3050,#18121f)",
  "radial-gradient(circle at 60% 40%,#2a3a4a,#12181f)",
  "radial-gradient(circle at 50% 50%,#453045,#191219)",
  "radial-gradient(circle at 30% 60%,#4a3030,#1f1414)",
];

function formatCompactUsd(n: number): string {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (n >= 1_000) return `$${Math.round(n / 1000)}K`;
  return `$${Math.round(n)}`;
}

interface ApiSceneRef {
  id: string;
  name: string;
  episode?: string | null;
}

interface ApiContentAssetSummary {
  id: string;
  title: string;
  format: string;
  estimated_value_usd?: number | null;
  scenes: ApiSceneRef[];
}

interface ApiSceneOpportunity {
  id: string;
  category: string;
  estimated_value_usd?: number | null;
  is_primary?: boolean;
}

interface ContentBreakdown {
  contentRevenue: ContentRevenue[];
  categorySegments: CategorySegment[];
  topScenes: TopScene[];
}

/**
 * Derives the three "story" analytics panels (content-type revenue, category
 * mix, top scenes) from data GET /content and GET /scenes/:id/opportunities
 * genuinely return, instead of the static fixture constants those panels
 * used to render unconditionally. Best-effort throughout: a single scene's
 * opportunity lookup failing just drops that scene rather than the whole
 * page. Returns null (never partial fixture-mixed-with-live data) when the
 * content list itself can't be fetched — AnalyticsView falls back to the
 * fixture constants, clearly marked, in that case.
 */
async function fetchContentBreakdown(): Promise<ContentBreakdown | null> {
  if (!API_BASE) return null;
  try {
    const res = await fetch(`${API_BASE}/api/v1/content`, { next: { revalidate: 60 } });
    if (!res.ok) {
      if (CONTEST_MODE) throw new Error(`Content API returned ${res.status}`);
      return null;
    }
    const data = (await res.json()) as { items?: ApiContentAssetSummary[] };
    const assets = data.items ?? [];

    // Revenue by content type: sum each asset's real estimated placement
    // value (GET /content) by format.
    const formatTotals = new Map<string, number>();
    for (const a of assets) {
      const v = a.estimated_value_usd ?? 0;
      if (v <= 0) continue;
      formatTotals.set(a.format, (formatTotals.get(a.format) ?? 0) + v);
    }
    const formatRows = [...formatTotals.entries()].sort((a, b) => b[1] - a[1]);
    const maxFormatValue = formatRows[0]?.[1] ?? 0;
    const contentRevenue: ContentRevenue[] = formatRows.map(([format, value]) => ({
      key: FORMAT_LABELS[format] ?? format,
      value: formatCompactUsd(value),
      percent: maxFormatValue > 0 ? Math.round((value / maxFormatValue) * 100) : 0,
    }));

    // Category mix + top scenes both need each scene's opportunity list —
    // fetch once per scene, best-effort.
    const sceneRefs = assets.flatMap((a) =>
      a.scenes.map((s) => ({ ...s, assetTitle: a.title })),
    );
    const sceneResults = await Promise.all(
      sceneRefs.map(async (s) => {
        try {
          const r = await fetch(
            `${API_BASE}/api/v1/scenes/${encodeURIComponent(s.id)}/opportunities`,
            { next: { revalidate: 60 } },
          );
          if (!r.ok) return null;
          const d = (await r.json()) as { items?: ApiSceneOpportunity[] };
          return { scene: s, items: d.items ?? [] };
        } catch {
          return null;
        }
      }),
    );

    const categoryTotals = new Map<string, number>();
    const sceneValues: { name: string; show: string; value: number }[] = [];
    for (const result of sceneResults) {
      if (!result) continue;
      const { scene, items } = result;
      let best = 0;
      for (const opp of items) {
        const v = opp.estimated_value_usd ?? 0;
        categoryTotals.set(opp.category, (categoryTotals.get(opp.category) ?? 0) + v);
        if (v > best) best = v;
      }
      if (best > 0) {
        sceneValues.push({
          name: scene.name,
          show: scene.episode ? `${scene.assetTitle} · ${scene.episode}` : scene.assetTitle,
          value: best,
        });
      }
    }

    const categoryRows = [...categoryTotals.entries()]
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1]);
    const top3 = categoryRows.slice(0, 3);
    const otherTotal = categoryRows.slice(3).reduce((sum, [, v]) => sum + v, 0);
    const segmentsRaw: [string, number][] = otherTotal > 0 ? [...top3, ["Other", otherTotal]] : top3;
    const categoryTotal = segmentsRaw.reduce((sum, [, v]) => sum + v, 0);
    const categorySegments: CategorySegment[] = [];
    if (categoryTotal > 0) {
      let allocated = 0;
      segmentsRaw.forEach(([label, v], i) => {
        const isLast = i === segmentsRaw.length - 1;
        const pct = isLast ? 100 - allocated : Math.round((v / categoryTotal) * 100);
        allocated += pct;
        categorySegments.push({
          label,
          color: CATEGORY_COLORS[i] ?? CATEGORY_COLORS[CATEGORY_COLORS.length - 1],
          pct,
        });
      });
    }

    const topScenes: TopScene[] = sceneValues
      .sort((a, b) => b.value - a.value)
      .slice(0, 4)
      .map((s, i) => ({
        name: s.name,
        show: s.show,
        value: formatCompactUsd(s.value),
        gold: i === 0,
        thumbGradient: SCENE_GRADIENTS[i % SCENE_GRADIENTS.length],
      }));

    return { contentRevenue, categorySegments, topScenes };
  } catch (err) {
    if (CONTEST_MODE) throw err;
    return null;
  }
}

interface ApiAnalyticsSummary {
  approved_deals: number;
  approved_revenue_usd: number;
  total_opportunities: number;
  total_campaigns: number;
  total_scenes: number;
  total_matches: number;
}

function summaryToStats(s: ApiAnalyticsSummary): AnalyticsStat[] {
  const fmt = (n: number) =>
    n >= 1_000_000
      ? `$${(n / 1_000_000).toFixed(2)}M`
      : n >= 1_000
        ? `$${Math.round(n / 1_000)}K`
        : `$${n.toFixed(0)}`;

  return [
    { label: "Content scanned", value: `${s.total_scenes} title${s.total_scenes !== 1 ? "s" : ""}` },
    { label: "Opportunities", value: String(s.total_opportunities) },
    { label: "Qualified matches", value: String(s.total_matches) },
    { label: "Deals closed", value: String(s.approved_deals) },
    { label: "Est. placement revenue", value: "$4.8M", modelled: true },
    { label: "Approved revenue", value: fmt(s.approved_revenue_usd), color: "gold" },
    { label: "Time saved", value: "340 hrs", color: "green", modelled: true },
    { label: "Approval cycle", value: "1.8 days", modelled: true },
  ];
}

async function fetchAnalyticsSummary(): Promise<AnalyticsStat[] | null> {
  if (!API_BASE) return null;
  try {
    const res = await fetch(`${API_BASE}/api/v1/analytics/summary`, {
      cache: "no-store",
    });
    if (!res.ok) {
      if (CONTEST_MODE) throw new Error(`Analytics API returned ${res.status}`);
      return null;
    }
    const data = await res.json() as ApiAnalyticsSummary;
    return summaryToStats(data);
  } catch (err) {
    if (CONTEST_MODE) throw err;
    return null;
  }
}

export default async function AnalyticsPage() {
  const [liveStats, liveBreakdown] = await Promise.all([
    fetchAnalyticsSummary(),
    fetchContentBreakdown(),
  ]);
  const dataSource = dataSourceFor(Boolean(API_BASE), Boolean(liveStats));
  return (
    <AnalyticsView
      liveStats={liveStats ?? undefined}
      dataSource={dataSource}
      liveContentRevenue={liveBreakdown?.contentRevenue.length ? liveBreakdown.contentRevenue : undefined}
      liveCategorySegments={liveBreakdown?.categorySegments.length ? liveBreakdown.categorySegments : undefined}
      liveTopScenes={liveBreakdown?.topScenes.length ? liveBreakdown.topScenes : undefined}
    />
  );
}

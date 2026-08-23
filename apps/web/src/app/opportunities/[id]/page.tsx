import { notFound } from "next/navigation";
import { OpportunityDetailView } from "@/components/opportunity/OpportunityDetailView";
import { getOpportunityById } from "@/data/opportunities";
import type { Complexity, OpportunityDetail, RightsStatus } from "@/lib/types";
import { IS_CONTEST_MODE as CONTEST_MODE } from "@/lib/contest-mode";
import { dataSourceFor } from "@/lib/data-source";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface OpportunityPageProps {
  params: Promise<{ id: string }>;
}

interface ApiOpportunityRow {
  id: string;
  scene_id?: string;
  asset_id?: string;
  category?: string;
  object_label?: string;
  timecode_start?: string;
  timecode_end?: string;
  screen_time_seconds?: number;
  naturalness_score?: number;
  brand_safety_score?: number;
  complexity?: string;
  rights_status?: string;
  estimated_value_usd?: number;
  is_primary?: boolean;
}

interface ApiMatchesResponse {
  opportunity_id: string;
  total_scanned?: number;
  ranked_count?: number;
  mcp_latency_ms?: number;
  matches: Record<string, unknown>[];
}

/** Median of the (budget_min_usd + budget_max_usd)/2 midpoints across ranked matches. */
function medianBudgetMidpoint(matches: Record<string, unknown>[]): number | null {
  const midpoints = matches
    .map((m) => {
      const lo = m.budget_min_usd as number | undefined;
      const hi = m.budget_max_usd as number | undefined;
      return lo != null && hi != null ? (lo + hi) / 2 : null;
    })
    .filter((v): v is number => v != null)
    .sort((a, b) => a - b);
  if (midpoints.length === 0) return null;
  const mid = Math.floor(midpoints.length / 2);
  return midpoints.length % 2 !== 0
    ? midpoints[mid]
    : (midpoints[mid - 1] + midpoints[mid]) / 2;
}

function apiOpportunityToDetail(
  o: ApiOpportunityRow,
  matchesData: ApiMatchesResponse | null,
): OpportunityDetail {
  const estUsd = o.estimated_value_usd ?? 0;
  const estimatedValue = estUsd > 0 ? `$${Math.round(estUsd).toLocaleString()}` : "TBD";
  const screenTimeSec = Math.round(o.screen_time_seconds ?? 0);
  const naturalness = Math.round(o.naturalness_score ?? 0);
  const brandSafety = Math.round(o.brand_safety_score ?? 0);
  const complexity = (o.complexity as Complexity) ?? "Medium";
  const rights = (o.rights_status as RightsStatus) ?? "Review";
  const category = o.category ?? "Uncategorized";
  const object = o.object_label ?? "Placement";
  const timecode =
    o.timecode_start && o.timecode_end ? `${o.timecode_start}–${o.timecode_end}` : "";

  const totalScanned = matchesData?.total_scanned;
  const rankedCount = matchesData?.ranked_count;
  const medianFee = matchesData ? medianBudgetMidpoint(matchesData.matches) : null;

  return {
    id: o.id,
    sceneId: o.scene_id ?? "",
    category,
    object,
    timecode,
    screenTime: `${screenTimeSec}s`,
    naturalness,
    brandSafety,
    complexity,
    rights,
    estimatedValue,
    primary: Boolean(o.is_primary),
    slug: o.id,
    title: `${object} Placement`,
    description: `${category} placement opportunity · ${screenTimeSec}s of screen time · rights ${rights.toLowerCase()}.`,
    metrics: [
      { key: "Naturalness", value: String(naturalness), color: naturalness >= 80 ? "green" : "ink", barPercent: naturalness },
      { key: "Brand safety", value: String(brandSafety), color: brandSafety >= 80 ? "green" : "ink", barPercent: brandSafety },
      { key: "Screen time", value: `${screenTimeSec}s` },
      { key: "Technical complexity", value: complexity },
      { key: "Rights status", value: rights, color: rights === "Clear" ? "green" : "ink" },
    ],
    compatibleCategories: [category],
    territories: [],
    clickhouseSignals: {
      comparableDeals: totalScanned != null ? `${totalScanned} scanned` : "N/A",
      medianFee: medianFee != null ? `$${Math.round(medianFee).toLocaleString()}` : "N/A",
      categoryDemand: rankedCount != null ? `${rankedCount} qualified matches` : "N/A",
    },
  };
}

async function fetchOpportunityFromApi(
  id: string,
): Promise<{ detail: OpportunityDetail; hadMatches: boolean } | null> {
  if (!API_BASE) return null;
  try {
    const [oppRes, matchesRes] = await Promise.all([
      fetch(`${API_BASE}/api/v1/opportunities/${encodeURIComponent(id)}`, { next: { revalidate: 60 } }),
      fetch(`${API_BASE}/api/v1/opportunities/${encodeURIComponent(id)}/matches`, { next: { revalidate: 60 } }),
    ]);
    if (!oppRes.ok) {
      if (CONTEST_MODE) throw new Error(`Opportunities API returned ${oppRes.status}`);
      return null;
    }
    const o = await oppRes.json() as ApiOpportunityRow;
    const matchesData = matchesRes.ok ? await matchesRes.json() as ApiMatchesResponse : null;
    return { detail: apiOpportunityToDetail(o, matchesData), hadMatches: matchesData !== null };
  } catch (err) {
    if (CONTEST_MODE) throw err;
    return null;
  }
}

export default async function OpportunityPage({ params }: OpportunityPageProps) {
  const { id } = await params;

  const apiResult = await fetchOpportunityFromApi(id);
  const opportunity = apiResult?.detail ?? getOpportunityById(id);

  if (!opportunity) {
    notFound();
  }

  // `clickhouseSignals` (comparable deals, median fee, category demand) is
  // sourced from the matches fetch, not the opportunity fetch — if matches
  // fails while the opportunity itself succeeds, those figures silently
  // degrade to "N/A" and the notice needs to say so rather than stay quiet.
  const dataSource = dataSourceFor(Boolean(API_BASE), Boolean(apiResult) && apiResult?.hadMatches === true);

  return <OpportunityDetailView opportunity={opportunity} dataSource={dataSource} />;
}

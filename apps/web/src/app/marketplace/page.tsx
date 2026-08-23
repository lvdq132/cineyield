import { MarketplaceView } from "@/components/marketplace/MarketplaceView";
import {
  demoMatchBreakdown,
  demoMatches,
  demoTopMatch,
} from "@/data/matches";
import type { CampaignMatch, MatchBreakdown, TopMatch } from "@/lib/types";
import { IS_CONTEST_MODE as CONTEST_MODE } from "@/lib/contest-mode";
import { dataSourceFor } from "@/lib/data-source";

// The seeded canonical opportunity used in the demo flow
const CANONICAL_OPP_ID = "opp_horizons_rooftop_001";
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// Transform backend CampaignMatch → frontend TopMatch for the #1 ranked match
function toTopMatch(m: Record<string, unknown>): TopMatch {
  const budgetMin = m.budget_min_usd as number | undefined;
  const budgetMax = m.budget_max_usd as number | undefined;
  const budget =
    budgetMin != null && budgetMax != null
      ? `$${Math.round(budgetMin / 1000)}K–$${Math.round(budgetMax / 1000)}K`
      : "N/A";
  const territories = (m.territories as string[] | undefined) ?? [];
  return {
    brand: String(m.brand ?? ""),
    product: String(m.product_line ?? m.campaign_name ?? ""),
    campaign: String(m.campaign_name ?? ""),
    score: Math.round(Number(m.score ?? 0)),
    budget,
    visibility: "10–30s",
    territories: territories.join(" + ") || "Global",
    exclusivity: "Category",
  };
}

// Transform backend CampaignMatch → frontend CampaignMatch (secondary card)
function toCampaignMatch(m: Record<string, unknown>, idx: number): CampaignMatch {
  const budgetMin = m.budget_min_usd as number | undefined;
  const budgetMax = m.budget_max_usd as number | undefined;
  const territories = (m.territories as string[] | undefined) ?? [];
  const budget =
    budgetMin != null && budgetMax != null
      ? `$${Math.round(budgetMin / 1000)}K–$${Math.round(budgetMax / 1000)}K`
      : "";
  const line = m.blocked_reason
    ? String(m.blocked_reason)
    : [m.campaign_name, budget, territories.slice(0, 2).join(" + ")]
        .filter(Boolean)
        .join(" · ");
  return {
    id: String(m.campaign_id ?? idx),
    brand: String(m.brand ?? ""),
    line,
    score: Math.round(Number(m.score ?? 0)),
    blocked: Boolean(m.is_blocked),
    statusLabel: m.is_blocked ? "BLOCKED" : undefined,
  };
}

// Transform the #1 match's score breakdown → MatchBreakdown[]
function toBreakdown(m: Record<string, unknown>): MatchBreakdown[] {
  const sb = (m.score_breakdown as Record<string, number>) ?? {};
  return [
    { key: "Context fit", value: Math.round(sb.context_fit ?? 0) },
    { key: "Category fit", value: Math.round(sb.category_fit ?? 0) },
    { key: "Visibility", value: Math.round(sb.visibility ?? 0) },
    { key: "Brand safety", value: Math.round(sb.brand_safety ?? 0) },
    { key: "Territory", value: Math.round(sb.territory ?? 0) },
    { key: "Budget & terms", value: Math.round(sb.budget_and_terms ?? 0) },
  ];
}

async function fetchMarketData(): Promise<{
  topMatch: TopMatch;
  matches: CampaignMatch[];
  breakdown: MatchBreakdown[];
  topCampaignId: string | undefined;
  totalScanned: number | undefined;
  rankedCount: number | undefined;
  mcpLatencyMs: number | undefined;
} | null> {
  if (!API_BASE) return null;

  const res = await fetch(
    `${API_BASE}/api/v1/opportunities/${CANONICAL_OPP_ID}/matches`,
    { next: { revalidate: 60 } },
  );
  if (!res.ok) {
    if (CONTEST_MODE) throw new Error(`Marketplace API returned ${res.status}`);
    return null;
  }
  const data = await res.json() as {
    matches: Record<string, unknown>[];
    total_scanned?: number;
    ranked_count?: number;
    mcp_latency_ms?: number;
  };
  const all = data.matches ?? [];
  if (all.length === 0) return null;

  const top = all[0];
  const rest = all.slice(1);
  return {
    topMatch: toTopMatch(top),
    matches: rest.map(toCampaignMatch),
    breakdown: toBreakdown(top),
    topCampaignId: String(top.campaign_id ?? ""),
    totalScanned: data.total_scanned,
    rankedCount: data.ranked_count,
    mcpLatencyMs: data.mcp_latency_ms,
  };
}

export default async function MarketplacePage() {
  let topMatch = demoTopMatch;
  let matches = demoMatches;
  let breakdown = demoMatchBreakdown;
  let topCampaignId: string | undefined;
  let totalScanned: number | undefined;
  let rankedCount: number | undefined;
  let mcpLatencyMs: number | undefined;

  const live = await fetchMarketData().catch((err) => {
    if (CONTEST_MODE) throw err;
    return null;
  });

  if (live) {
    topMatch = live.topMatch;
    matches = live.matches;
    breakdown = live.breakdown;
    topCampaignId = live.topCampaignId;
    totalScanned = live.totalScanned;
    rankedCount = live.rankedCount;
    mcpLatencyMs = live.mcpLatencyMs;
  }

  const dataSource = dataSourceFor(Boolean(API_BASE), Boolean(live));

  return (
    <MarketplaceView
      topMatch={topMatch}
      matches={matches}
      breakdown={breakdown}
      opportunityId={CANONICAL_OPP_ID}
      topCampaignId={topCampaignId}
      totalScanned={totalScanned}
      rankedCount={rankedCount}
      mcpLatencyMs={mcpLatencyMs}
      dataSource={dataSource}
    />
  );
}

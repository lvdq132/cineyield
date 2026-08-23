import { LibraryView } from "@/components/library/LibraryView";
import { demoCatalog } from "@/data/content";
import type { ContentProject, LibraryStat, AnalysisStatus, ContentFormat } from "@/lib/types";
import { IS_CONTEST_MODE as CONTEST_MODE } from "@/lib/contest-mode";
import { dataSourceFor } from "@/lib/data-source";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

/** Shapes returned by GET /api/v1/content — see cineyield/schemas/content.py. */
interface ApiContentScene {
  id: string;
  name: string;
}
interface ApiContentAsset {
  id: string;
  title: string;
  subtitle: string;
  format: string;
  status: string;
  scene_count: number;
  opportunity_count: number;
  estimated_value_usd?: number | null;
  updated_at?: string | null;
  scenes: ApiContentScene[];
}
interface ApiContentList {
  items: ApiContentAsset[];
  total: number;
}
/** Shape of GET /api/v1/scenes/{id}/opportunities — only `items.length` is used here. */
interface ApiSceneOpportunities {
  items: unknown[];
}
interface ApiAnalyticsSummary {
  total_scenes: number;
  total_opportunities: number;
  total_matches: number;
  approved_deals: number;
  approved_revenue_usd: number;
}

/**
 * The card gradients are presentation, not data — ClickHouse has no business
 * storing a CSS gradient. Reuse the fixture gradient for known assets so live
 * mode looks identical to the design, and fall back to a neutral one for any
 * asset the fixtures do not know about (e.g. one a judge just uploaded).
 */
const FALLBACK_GRADIENT =
  "radial-gradient(120% 100% at 40% 25%,#2f3340,#1e2028 55%,#0c0d10)";

function gradientFor(id: string): string {
  return demoCatalog.find((c) => c.id === id)?.thumbnailGradient ?? FALLBACK_GRADIENT;
}

function formatUsd(v?: number | null): string {
  if (!v || v <= 0) return "—";
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `$${Math.round(v / 1_000)}K`;
  return `$${Math.round(v)}`;
}

/** "2h ago" style relative label from an ISO timestamp. */
function relativeTime(iso?: string | null): string {
  if (!iso) return "—";
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return "—";
  const mins = Math.max(0, Math.round((Date.now() - then) / 60_000));
  if (mins < 1) return "live";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

function normaliseFormat(f: string): ContentFormat {
  // Backend enum is snake_case (tv_series); the design language is "tv series".
  return f.replace(/_/g, " ") as ContentFormat;
}

function normaliseStatus(s: string): AnalysisStatus {
  return (s.charAt(0).toUpperCase() + s.slice(1)) as AnalysisStatus;
}

/**
 * `content_assets.opportunity_count` is seeded catalogue metadata (e.g. a
 * series really does have 47 opportunities once fully analyzed) — it is not
 * how many the pipeline has actually scored. Only the `scenes` table (the
 * analyzed subset embedded on the asset) holds real opportunities, so sum
 * them directly rather than trust the catalogue figure. Cheap in practice:
 * the whole demo catalogue has a dozen analyzed scenes total.
 */
async function realOpportunityCount(scenes: ApiContentScene[]): Promise<number | null> {
  if (scenes.length === 0) return 0; // nothing analyzed yet — genuinely zero, not unknown
  const counts = await Promise.all(
    scenes.map((s) => fetchJson<ApiSceneOpportunities>(`/api/v1/scenes/${encodeURIComponent(s.id)}/opportunities`)),
  );
  if (counts.some((c) => c === null)) return null; // a fetch failed — don't guess
  return counts.reduce((sum, c) => sum + (c as ApiSceneOpportunities).items.length, 0);
}

async function apiAssetToProject(a: ApiContentAsset): Promise<ContentProject> {
  const analyzed = a.scenes?.length ?? 0;
  const firstScene = a.scenes?.[0]?.id;
  const realOpps = await realOpportunityCount(a.scenes ?? []);
  return {
    id: a.id,
    title: a.title,
    subtitle: a.subtitle,
    format: normaliseFormat(a.format),
    status: normaliseStatus(a.status),
    // Displayed as "analyzed / catalogue" by LibraryView; keep the raw catalogue
    // figure here so the string stays meaningful if either field is missing.
    scenes: String(a.scene_count),
    // Real, analyzed-scene-derived count — never the catalogue's
    // `opportunity_count`, which can wildly overstate what's actually been
    // scored (e.g. 47 catalogued vs. 5 actually analyzed). "—" means the
    // real count could not be determined, not that it is zero.
    opportunities: realOpps !== null ? String(realOpps) : "—",
    estimatedValue: formatUsd(a.estimated_value_usd),
    updated: relativeTime(a.updated_at),
    thumbnailGradient: gradientFor(a.id),
    href: firstScene ? `/scene/${encodeURIComponent(firstScene)}` : undefined,
    analyzedScenes: analyzed,
    totalScenes: a.scene_count,
  };
}

async function fetchJson<T>(path: string): Promise<T | null> {
  if (!API_BASE) return null;
  try {
    const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
    if (!res.ok) {
      if (CONTEST_MODE) throw new Error(`${path} returned ${res.status}`);
      return null;
    }
    return (await res.json()) as T;
  } catch (err) {
    if (CONTEST_MODE) throw err;
    return null;
  }
}

/**
 * Headline stats, computed from the real analytics aggregate rather than the
 * fixture constants. Every figure here is a genuine ClickHouse count.
 */
function summaryToLibraryStats(s: ApiAnalyticsSummary): LibraryStat[] {
  return [
    { label: "Scenes analyzed", value: String(s.total_scenes) },
    { label: "Opportunities", value: String(s.total_opportunities) },
    { label: "Qualified matches", value: String(s.total_matches) },
    { label: "Deals approved", value: String(s.approved_deals), color: "amber" },
  ];
}

export const dynamic = "force-dynamic";

export default async function LibraryPage() {
  const [list, summary] = await Promise.all([
    fetchJson<ApiContentList>("/api/v1/content"),
    fetchJson<ApiAnalyticsSummary>("/api/v1/analytics/summary"),
  ]);

  // Fetch succeeding is what makes data live — not whether it happened to
  // come back non-empty. A 200 {"items":[],"total":0} is a legitimate empty
  // catalogue, not a failure, and must not render fixtures under an
  // "unreachable" banner.
  const usedLiveList = list !== null;
  const catalog = list !== null ? await Promise.all(list.items.map(apiAssetToProject)) : demoCatalog;
  const stats = summary ? summaryToLibraryStats(summary) : undefined;
  const approvedRevenue = summary ? formatUsd(summary.approved_revenue_usd) : undefined;
  // The hero strip draws its stats from `summary`, not `list` — if `/content`
  // succeeds but `/analytics/summary` fails, LibraryView silently falls back
  // to fixture stats while the catalog below renders live. The notice has to
  // reflect the worse of the two fetches, or it stays hidden while fixture
  // numbers sit under a "live" catalog.
  const dataSource = dataSourceFor(Boolean(API_BASE), usedLiveList && summary !== null);

  return (
    <LibraryView
      catalog={catalog}
      stats={stats}
      approvedRevenue={approvedRevenue}
      dataSource={dataSource}
    />
  );
}

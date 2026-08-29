import { notFound } from "next/navigation";
import { SceneView } from "@/components/scene/SceneView";
import { getSceneById } from "@/data/scenes";
import { getOpportunitiesForScene } from "@/data/opportunities";
import type { Complexity, Opportunity, RightsStatus, Scene } from "@/lib/types";
import { IS_CONTEST_MODE as CONTEST_MODE } from "@/lib/contest-mode";
import { dataSourceFor } from "@/lib/data-source";
import { resolveApiUrl } from "@/lib/api-client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface ScenePageProps {
  params: Promise<{ id: string }>;
}

/** Row shape from GET /api/v1/scenes/{id}/opportunities. */
interface ApiOpportunityRow {
  id: string;
  scene_id?: string;
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
  placement_zone?: string;
  placement_notes?: string;
}

/**
 * The scene "player" is an abstract gradient stand-in for footage (the demo
 * stores no video frames). The detection overlay visualises the objects Gemini
 * actually detected; the box *positions* are illustrative, laid out on a fixed
 * set of slots so every scene renders like the designed fixture instead of an
 * empty rectangle. Without this, live scenes (Harbor Signal, and even Rooftop
 * Reflection once it loads live) showed a blank player with no overlay.
 */
const BOX_LAYOUTS = [
  { x: 30, y: 46, width: 16, height: 18 },
  { x: 58, y: 58, width: 10, height: 14 },
  { x: 72, y: 40, width: 12, height: 22 },
];

function detectionBoxesFrom(oppRows: ApiOpportunityRow[]) {
  const primaryFirst = [...oppRows].sort(
    (a, b) => Number(Boolean(b.is_primary)) - Number(Boolean(a.is_primary)),
  );
  return primaryFirst.slice(0, BOX_LAYOUTS.length).map((o, i) => ({
    label: o.object_label ?? o.category ?? "Placement",
    confidence: Math.round(o.naturalness_score ?? 88),
    ...BOX_LAYOUTS[i],
    primary: i === 0,
  }));
}

function normaliseComplexity(v?: string): Complexity {
  const s = (v ?? "").toLowerCase();
  return s === "high" ? "High" : s === "low" ? "Low" : "Medium";
}

function normaliseRights(v?: string): RightsStatus {
  return (v ?? "").toLowerCase() === "clear" ? "Clear" : "Review";
}

function apiOpportunityToOpportunity(o: ApiOpportunityRow, sceneId: string): Opportunity {
  const est = o.estimated_value_usd ?? 0;
  return {
    id: o.id,
    sceneId: o.scene_id ?? sceneId,
    category: o.category ?? "Uncategorized",
    object: o.object_label ?? "Placement",
    timecode:
      o.timecode_start && o.timecode_end ? `${o.timecode_start}–${o.timecode_end}` : "",
    screenTime: `${Math.round(o.screen_time_seconds ?? 0)}s`,
    naturalness: Math.round(o.naturalness_score ?? 0),
    brandSafety: Math.round(o.brand_safety_score ?? 0),
    complexity: normaliseComplexity(o.complexity),
    rights: normaliseRights(o.rights_status),
    estimatedValue: est > 0 ? `$${Math.round(est).toLocaleString()}` : "TBD",
    primary: Boolean(o.is_primary),
    placementZone: o.placement_zone ?? "",
    placementNotes: o.placement_notes ?? "",
  };
}

interface ApiSceneResult {
  scene: Scene;
  /** null means the opportunities fetch itself failed — distinct from a scene with none. */
  opportunities: Opportunity[] | null;
}

async function fetchSceneFromApi(id: string): Promise<ApiSceneResult | null> {
  if (!API_BASE) return null;
  try {
    const [sceneRes, oppsRes] = await Promise.all([
      fetch(`${API_BASE}/api/v1/scenes/${encodeURIComponent(id)}`, { next: { revalidate: 60 } }),
      fetch(`${API_BASE}/api/v1/scenes/${encodeURIComponent(id)}/opportunities`, { next: { revalidate: 60 } }),
    ]);
    if (!sceneRes.ok) {
      if (CONTEST_MODE) throw new Error(`Scene API returned ${sceneRes.status}`);
      return null;
    }
    const s = await sceneRes.json() as Record<string, unknown>;
    const media = (s.media ?? null) as {
      frame_url?: string;
      segment_url?: string;
      frame_time_seconds?: number;
      source_duration_seconds?: number;
    } | null;

    let oppRows: ApiOpportunityRow[] | null = null;
    if (oppsRes.ok) {
      const oppsJson = await oppsRes.json() as { items: ApiOpportunityRow[] };
      oppRows = oppsJson.items ?? [];
    } else if (CONTEST_MODE) {
      throw new Error(`Scene opportunities API returned ${oppsRes.status}`);
    }

    const scene: Scene = {
      id: String(s.scene_id ?? id),
      projectId: String(s.asset_id ?? ""),
      projectTitle: String(s.asset_id ?? "").toUpperCase(),
      episode: "",
      name: String(s.name ?? "Scene"),
      summary: String(s.summary ?? ""),
      brandSafety: Number(s.brand_safety_score ?? 70),
      narrativeWeight: String(s.narrative_weight ?? "Medium"),
      mood: String(s.mood ?? ""),
      duration: "00:44",
      currentTime: "00:00",
      playerGradient: "radial-gradient(130% 100% at 50% 14%,#1e3a5f 0%,#15243a 44%,#0d0b0f 100%)",
      detectedObjects: ((s.detected_objects as Array<Record<string, unknown>> | undefined) ?? [])
        .slice(0, 8)
        .map((o) => ({
          label: String(o.label ?? "Object"),
          category: String(o.category ?? "Other"),
          confidence: Math.round(Number(o.confidence ?? 0)),
          isPrimary: Boolean(o.is_primary),
        })),
      detectionBoxes: detectionBoxesFrom(oppRows ?? []),
      frameUrl: resolveApiUrl(media?.frame_url) ?? undefined,
      videoUrl: resolveApiUrl(media?.segment_url) ?? undefined,
      frameTimeSeconds: media?.frame_time_seconds,
      sourceDurationSeconds: media?.source_duration_seconds,
    };

    return {
      scene,
      opportunities: oppRows ? oppRows.map((o) => apiOpportunityToOpportunity(o, scene.id)) : null,
    };
  } catch (err) {
    if (CONTEST_MODE) throw err;
    return null;
  }
}

export default async function ScenePage({ params }: ScenePageProps) {
  const { id } = await params;

  const apiResult = await fetchSceneFromApi(id);
  const scene = apiResult?.scene ?? getSceneById(id);

  if (!scene) {
    notFound();
  }

  // Opportunities were previously always fixtures (getOpportunitiesForScene),
  // regardless of whether the scene itself came back live — the canonical
  // demo scene (rooftop-reflection) fetched real, but rendered fixture
  // opportunities beside it under a "live" badge with no notice. Fetch the
  // real ones, and fall back only when that specific fetch failed.
  const opportunities = apiResult?.opportunities ?? getOpportunitiesForScene(id);
  const dataSource = dataSourceFor(
    Boolean(API_BASE),
    Boolean(apiResult) && apiResult?.opportunities !== null,
  );

  return <SceneView scene={scene} opportunities={opportunities} dataSource={dataSource} />;
}

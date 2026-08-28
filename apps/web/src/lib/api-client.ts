/**
 * CineYield API client — typed boundary between frontend and agent API.
 *
 * Falls back to fixture data when NEXT_PUBLIC_API_URL is unset (local demo mode).
 * Remove fixtures and set NEXT_PUBLIC_API_URL=http://localhost:8000 to go live.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

// ─── Low-level fetch ──────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_BASE) {
    throw new ApiError(503, "API_NOT_CONFIGURED", "Set NEXT_PUBLIC_API_URL to connect to the backend");
  }
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      body.error ?? "api_error",
      body.detail ?? body.message ?? res.statusText,
    );
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ─── Health ───────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
}

export interface ReadinessResponse {
  status: "ok" | "degraded";
  checks: Record<string, { status: string; message?: string }>;
}

export const health = {
  check: () => apiFetch<HealthResponse>("/health"),
  ready: () => apiFetch<ReadinessResponse>("/ready"),
};

// ─── Content assets ───────────────────────────────────────────────────────────

export interface ApiContentAsset {
  id: string;
  title: string;
  format: string;
  status: string;
  scene_count?: number;
  opportunity_count?: number;
  estimated_value_usd?: number;
  updated_at?: string;
}

export interface ContentListResponse {
  items: ApiContentAsset[];
  total: number;
}

export const content = {
  list: () => apiFetch<ContentListResponse>("/api/v1/content"),
  get: (assetId: string) => apiFetch<ApiContentAsset>(`/api/v1/content/${assetId}`),
};

// ─── Scenes ───────────────────────────────────────────────────────────────────

export interface ApiDetectedObject {
  label: string;
  category: string;
  confidence: number;
  is_primary?: boolean;
  timecode_start?: string;
  timecode_end?: string;
}

export interface ApiScene {
  scene_id: string;
  asset_id: string;
  name: string;
  summary: string;
  mood: string;
  narrative_weight: string;
  brand_safety_score: number;
  duration_seconds: number;
  detected_objects: ApiDetectedObject[];
  gemini_model_used?: string;
  analyzed_at?: string;
}

export interface SceneOpportunitiesResponse {
  scene_id: string;
  items: ApiOpportunity[];
  total: number;
}

export const scenes = {
  get: (sceneId: string) => apiFetch<ApiScene>(`/api/v1/scenes/${sceneId}`),
  opportunities: (sceneId: string) =>
    apiFetch<SceneOpportunitiesResponse>(`/api/v1/scenes/${sceneId}/opportunities`),
};

// ─── Opportunities ────────────────────────────────────────────────────────────

export interface ApiOpportunity {
  id: string;
  scene_id: string;
  category: string;
  territories: string[];
  screen_time_seconds: number;
  estimated_value_usd: number;
  confidence?: number;
}

export interface OpportunitiesListResponse {
  items: ApiOpportunity[];
  total: number;
}

export interface ApiCampaignMatch {
  id: string;
  brand: string;
  campaign_name: string;
  composite_score: number;
  is_blocked: boolean;
  blocked_reason?: string;
  context_fit?: number;
  category_fit?: number;
  visibility_score?: number;
  brand_safety?: number;
  territory_score?: number;
  budget_score?: number;
}

export interface MatchesResponse {
  opportunity_id: string;
  total_scanned: number;
  ranked_count: number;
  matches: ApiCampaignMatch[];
  mcp_latency_ms?: number;
}

export interface ProposeResponse {
  proposal_id: string;
  brand_name: string;
  campaign_name: string;
  placement_fee_usd: number;
  brand_brief: string;
  scene_title: string;
  scene_description: string;
  composite_score: number;
  terms: unknown[];
  guardrails: unknown[];
}

export const opportunities = {
  list: (sceneId?: string) => {
    const qs = sceneId ? `?scene_id=${encodeURIComponent(sceneId)}` : "";
    return apiFetch<OpportunitiesListResponse>(`/api/v1/opportunities${qs}`);
  },
  get: (opportunityId: string) =>
    apiFetch<ApiOpportunity>(`/api/v1/opportunities/${opportunityId}`),
  matches: (opportunityId: string) =>
    apiFetch<MatchesResponse>(`/api/v1/opportunities/${opportunityId}/matches`),
  propose: (opportunityId: string, campaignId: string) =>
    apiFetch<ProposeResponse>(`/api/v1/opportunities/${opportunityId}/propose`, {
      method: "POST",
      body: JSON.stringify({ campaign_id: campaignId }),
    }),
};

// ─── Deals / Proposals ────────────────────────────────────────────────────────

export interface ApiProposal {
  id: string;
  opportunity_id: string;
  campaign_id: string;
  brand: string;
  campaign_name: string;
  composite_score: number;
  placement_fee_usd?: number;
  status: string;
  created_at?: string;
}

export interface DealsListResponse {
  items: ApiProposal[];
  total: number;
}

export interface ApproveRequest {
  approved: boolean;
  approver: string;
  note?: string;
}

export interface ApproveResponse {
  deal_id: string;
  approved: boolean;
  approver: string;
  status: "approved" | "rejected";
  revenue_event_id?: string;
}

export type DealDecisionAction = "approve" | "reject" | "counter" | "request_changes";

export interface DealDecisionResponse extends ApproveResponse {
  workflow_state?: string;
  action?: DealDecisionAction;
}

export const deals = {
  list: () => apiFetch<DealsListResponse>("/api/v1/deals"),
  get: (proposalId: string) => apiFetch<ApiProposal>(`/api/v1/deals/${proposalId}`),
  approve: (proposalId: string, body: ApproveRequest) =>
    apiFetch<ApproveResponse>(`/api/v1/deals/${proposalId}/approve`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  decide: (
    proposalId: string,
    body: { action: DealDecisionAction; approver: string; note?: string },
  ) =>
    apiFetch<DealDecisionResponse>(`/api/v1/deals/${proposalId}/decision`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

// ─── Ingest ───────────────────────────────────────────────────────────────────

export interface IngestJobResponse {
  job_id: string;
  asset_id: string;
  status: string;
  filename: string;
  size_bytes: number;
  submitted_at: string;
  message: string;
}

export interface JobStatusResponse {
  job_id: string;
  asset_id: string;
  status: "queued" | "analyzing" | "completed" | "failed" | "pending_credentials";
  submitted_at: string;
  completed_at?: string;
  error?: string;
  scene_analysis?: ApiScene;
}

export interface SupportedFormatsResponse {
  supported_mime_types: string[];
  max_file_size_mb: number;
  note: string;
}

export const ingest = {
  uploadVideo: async (file: File): Promise<IngestJobResponse> => {
    if (!API_BASE) {
      throw new ApiError(503, "API_NOT_CONFIGURED", "Set NEXT_PUBLIC_API_URL to connect to the backend");
    }
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/v1/ingest/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.error ?? "upload_error", body.detail ?? res.statusText);
    }
    return res.json();
  },

  pollStatus: (jobId: string) =>
    apiFetch<JobStatusResponse>(`/api/v1/ingest/status/${jobId}`),

  formats: () => apiFetch<SupportedFormatsResponse>("/api/v1/ingest/formats"),
};

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface AnalyticsSummaryResponse {
  approved_deals: number;
  approved_revenue_usd: number;
  total_opportunities: number;
  total_campaigns: number;
  total_scenes: number;
  total_matches: number;
}

export const analytics = {
  summary: () => apiFetch<AnalyticsSummaryResponse>("/api/v1/analytics/summary"),
};

// ─── Agent Events ─────────────────────────────────────────────────────────────

export interface AgentEventRecord {
  event_id: string;
  correlation_id: string;
  agent_name: string;
  kind: string;
  asset_id?: string;
  scene_id?: string;
  opportunity_id?: string;
  campaign_id?: string;
  tool_name?: string;
  summary: string;
  latency_ms?: number;
  success: boolean;
  occurred_at: string;
}

export interface AgentEventsResponse {
  events: AgentEventRecord[];
  count: number;
}

export const agentEvents = {
  list: (limit = 50, opportunityId?: string) => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (opportunityId) qs.set("opportunity_id", opportunityId);
    return apiFetch<AgentEventsResponse>(`/api/v1/agents/events?${qs}`);
  },
};

// ─── isApiAvailable guard ─────────────────────────────────────────────────────

/** Returns true when the backend URL is configured and reachable. */
export async function isApiAvailable(): Promise<boolean> {
  if (!API_BASE) return false;
  try {
    await health.check();
    return true;
  } catch {
    return false;
  }
}

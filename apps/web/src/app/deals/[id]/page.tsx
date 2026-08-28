import { notFound } from "next/navigation";
import { DealView } from "@/components/deal/DealView";
import { getProposalById } from "@/data/proposals";
import type { Guardrail, Proposal, ProposalTerm } from "@/lib/types";
import { IS_CONTEST_MODE as CONTEST_MODE } from "@/lib/contest-mode";
import { dataSourceFor } from "@/lib/data-source";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface DealPageProps {
  params: Promise<{ id: string }>;
}

interface ApiDeal {
  id: string;
  opportunity_id?: string;
  campaign_id?: string;
  brand_name?: string;
  campaign_name?: string;
  placement_fee_usd?: number;
  workflow_state?: string;
  brand_brief?: string;
  scene_title?: string;
  scene_description?: string;
  is_approved?: boolean;
}

/** One row of GET /api/v1/opportunities/{id}/matches — the only place the
 *  backend actually computes rights/territory/category fit for a campaign. */
interface ApiMatch {
  campaign_id: string;
  is_blocked?: boolean;
  blocked_reason?: string | null;
  territories?: string[];
  score_breakdown?: {
    territory?: number;
    category_fit?: number;
  };
}

/**
 * GET /api/v1/deals/{id} does not persist the terms or guardrails a
 * proposal was computed with — those only exist in the one-shot response of
 * POST .../propose, which this read-only page has no business re-invoking
 * (it would compose a brand-new LLM proposal every time someone opens the
 * link). So: terms/guardrails that ARE backed by a stable, re-fetchable
 * source (the opportunity's campaign match — territory, category fit, block
 * status) are derived from GET .../matches. Everything else is either
 * dropped or marked illustrative — never asserted as a pass the backend
 * never actually re-confirmed.
 */
function buildTermsAndGuardrails(
  d: ApiDeal,
  feeStr: string,
  match: ApiMatch | null,
): { terms: ProposalTerm[]; guardrails: Guardrail[] } {
  const territories = match?.territories ?? [];
  const territoryValue = match ? (territories.length ? territories.join(", ") : "None") : "Not available";

  const terms: ProposalTerm[] = [
    { label: "Placement fee", value: feeStr, highlight: true },
    { label: "Territory", value: territoryValue, modelled: !match },
    // No backend source persists these per-deal — shown as illustrative
    // deal-template terms, not confirmed facts about this specific deal.
    { label: "Payment model", value: "Flat fee", modelled: true },
    { label: "Usage window", value: "12 months", modelled: true },
    { label: "Exclusivity", value: "Category", modelled: true },
    { label: "Deliverables", value: "Episode + 2 cutdowns", modelled: true },
  ];

  if (!match) {
    return { terms, guardrails: [] };
  }

  const territoryScore = Math.round(match.score_breakdown?.territory ?? 0);
  const categoryScore = Math.round(match.score_breakdown?.category_fit ?? 0);
  const blocked = Boolean(match.is_blocked);

  const guardrails: Guardrail[] = [
    {
      name: "Territory Fit",
      detail: `${territoryScore}/100 · campaign covers ${territories.length ? territories.join(", ") : "no territories"}`,
      mark: territoryScore >= 50 ? "✓" : "!",
      status: territoryScore >= 50 ? "PASS" : "REVIEW",
      statusColor: territoryScore >= 50 ? "green" : "amber",
    },
    {
      name: "Guardrail Check",
      detail: blocked ? (match.blocked_reason ?? "Blocked by matching engine.") : "No blocking conflicts found for this match.",
      mark: blocked ? "!" : "✓",
      status: blocked ? "REVIEW" : "PASS",
      statusColor: blocked ? "amber" : "green",
    },
    {
      name: "Category Fit",
      detail: `${categoryScore}/100 · category & product alignment score`,
      mark: categoryScore >= 50 ? "✓" : "!",
      status: categoryScore >= 50 ? "PASS" : "REVIEW",
      statusColor: categoryScore >= 50 ? "green" : "amber",
    },
  ];

  return { terms, guardrails };
}

async function fetchMatchForDeal(
  opportunityId: string | undefined,
  campaignId: string | undefined,
): Promise<ApiMatch | null> {
  if (!opportunityId || !campaignId) return null;
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/opportunities/${encodeURIComponent(opportunityId)}/matches`,
      { next: { revalidate: 60 } },
    );
    if (!res.ok) return null;
    const data = await res.json() as { matches?: ApiMatch[] };
    return (data.matches ?? []).find((m) => m.campaign_id === campaignId) ?? null;
  } catch {
    return null;
  }
}

async function fetchDealFromApi(
  id: string,
): Promise<{
  proposal: Proposal;
  isApproved: boolean;
  workflowState: string;
  hadMatch: boolean;
} | null> {
  if (!API_BASE) return null;
  try {
    const res = await fetch(`${API_BASE}/api/v1/deals/${encodeURIComponent(id)}`, {
      cache: "no-store",
    });
    if (!res.ok) {
      if (CONTEST_MODE) throw new Error(`Deals API returned ${res.status}`);
      return null;
    }
    const d = await res.json() as ApiDeal;
    const fee = d.placement_fee_usd ?? 0;
    const feeStr = fee > 0 ? `$${fee.toLocaleString()}` : "TBD";

    // Matches enrichment is best-effort, same as the sibling scene/opportunity
    // pages: its failure doesn't invalidate the deal itself, but it does mean
    // territory/guardrails fall back to an honest "not available" state
    // rather than a fixture — see buildTermsAndGuardrails.
    const match = await fetchMatchForDeal(d.opportunity_id, d.campaign_id);
    const { terms, guardrails } = buildTermsAndGuardrails(d, feeStr, match);

    const proposal: Proposal = {
      id: d.id,
      brandName: d.brand_name ?? "Brand",
      campaignName: d.campaign_name ?? "",
      brandBrief: d.brand_brief ?? "",
      sceneTitle: d.scene_title ?? "Scene",
      sceneEpisode: "",
      sceneDetail: d.scene_description ?? "",
      sceneDescription: d.scene_description ?? "",
      placementFee: feeStr,
      terms,
      guardrails,
    };

    return {
      proposal,
      isApproved: Boolean(d.is_approved),
      workflowState: d.workflow_state ?? "PRODUCER_REVIEW",
      hadMatch: Boolean(match),
    };
  } catch (err) {
    if (CONTEST_MODE) throw err;
    return null;
  }
}

export default async function DealPage({ params }: DealPageProps) {
  const { id } = await params;

  const apiResult = await fetchDealFromApi(id);

  const proposal = apiResult?.proposal ?? getProposalById(id);
  const isApproved = apiResult?.isApproved ?? false;
  const workflowState = apiResult?.workflowState ?? "PRODUCER_REVIEW";

  if (!proposal) {
    notFound();
  }

  // Territory and guardrails come from a second fetch (opportunity matches)
  // layered on top of the deal fetch — if that second call fails, the terms
  // panel falls back to an honest "Not available" state rather than a
  // fixture, but the notice still needs to say this page isn't fully live.
  const dataSource = dataSourceFor(Boolean(API_BASE), Boolean(apiResult) && apiResult?.hadMatch === true);

  return (
    <DealView
      proposal={proposal}
      initialApproved={isApproved}
      initialWorkflowState={workflowState}
      dataSource={dataSource}
    />
  );
}

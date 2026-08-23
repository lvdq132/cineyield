import type { Proposal } from "@/lib/types";

/** @fixture Demo proposals/deals — replace with GET /api/deals/:id */
export const demoProposals: Record<string, Proposal> = {
  "aurelius-systems": {
    id: "aurelius-systems",
    brandName: "Aurelius Systems",
    campaignName: "Focus Without Limits",
    brandBrief:
      "Target 18–44, premium tech & design audience. Prefers aspirational, urban, focused, modern context. Excludes violence, intoxication, ridicule, unsafe use.",
    sceneTitle: "HORIZONS · S2E3",
    sceneEpisode: "Rooftop Reflection · 00:12–00:38",
    sceneDetail:
      "Aspirational dusk cityscape, reflective mood, wireless headphones already in frame. 26s screen time, high camera stability, brand safety 96.",
    sceneDescription: "",
    placementFee: "$185,000",
    terms: [
      { label: "Placement fee", value: "$185,000", highlight: true },
      { label: "Payment model", value: "Flat fee" },
      { label: "Usage window", value: "12 months" },
      { label: "Territory", value: "NA + selected EU" },
      { label: "Exclusivity", value: "Consumer audio" },
      { label: "Deliverables", value: "Episode + 2 cutdowns" },
    ],
    guardrails: [
      {
        name: "Rights Agent",
        detail: "Pass · 3 of 4 markets cleared",
        mark: "✓",
        status: "PASS",
        statusColor: "green",
      },
      {
        name: "Creative Guardian",
        detail: "No plot / motivation impact",
        mark: "✓",
        status: "PASS",
        statusColor: "green",
      },
      {
        name: "Brand Accuracy",
        detail: "Category & product align",
        mark: "✓",
        status: "PASS",
        statusColor: "green",
      },
      {
        name: "Germany (DE)",
        detail: "Usage window not cleared",
        mark: "!",
        status: "REVIEW",
        statusColor: "amber",
      },
    ],
  },
};

export const DEFAULT_DEAL_ID = "aurelius-systems";

export function getProposalById(id: string): Proposal | undefined {
  return demoProposals[id];
}

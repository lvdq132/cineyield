import type { CampaignMatch, MatchBreakdown, TopMatch } from "@/lib/types";

/** @fixture Demo campaigns/matches — replace with GET /api/opportunities/:id/matches */
export const demoTopMatch: TopMatch = {
  brand: "Aurelius Systems",
  product: "Aurelius One Wireless Headphones",
  campaign: "Focus Without Limits",
  score: 96,
  budget: "$150K–$250K",
  visibility: "10–30s",
  territories: "NA + EU",
  exclusivity: "Category",
};

export const demoMatches: CampaignMatch[] = [
  {
    id: "aurora-tech",
    brand: "Aurora Tech",
    line: "“Everyday Sound” · $90K–$160K · NA",
    score: 84,
  },
  {
    id: "pinnacle",
    brand: "Pinnacle Performance",
    line: "“Move Free” · $120K–$200K · NA + EU",
    score: 79,
  },
  {
    id: "nexalife",
    brand: "NexaLife",
    line: "“Balance” · $60K–$120K · EU",
    score: 73,
  },
  {
    id: "vortex",
    brand: "Vortex Energy",
    line: "Creative Guardian: adjacency conflicts with reflective tone",
    score: 41,
    blocked: true,
    statusLabel: "BLOCKED",
  },
  {
    id: "stride",
    brand: "Stride Apparel",
    line: "Rights: category mismatch — apparel not in scene",
    score: 38,
    blocked: true,
    statusLabel: "BLOCKED",
  },
];

// Breakdown reflects the real deterministic calculation:
// context_fit=99 (brand_safety 96 + narrative_weight=High +3), category_fit=100,
// visibility=80 (26s in 10–30s window), brand_safety=96, territory=100, budget=100
// composite = 99×0.25 + 100×0.25 + 80×0.15 + 96×0.20 + 100×0.10 + 100×0.05 = 96.0
export const demoMatchBreakdown: MatchBreakdown[] = [
  { key: "Context fit", value: 99 },
  { key: "Category fit", value: 100 },
  { key: "Visibility", value: 80 },
  { key: "Brand safety", value: 96 },
  { key: "Territory", value: 100 },
  { key: "Budget & terms", value: 100 },
];

export const MARKETPLACE_QUERY_SUMMARY =
  "27 campaigns scanned · 6 ranked · 45ms";

import type { Opportunity, OpportunityDetail } from "@/lib/types";

/** @fixture Demo opportunities — replace with GET /api/scenes/:id/opportunities */
export const demoOpportunities: Opportunity[] = [
  {
    id: "opp_horizons_rooftop_001",
    sceneId: "rooftop-reflection",
    category: "Consumer Audio",
    object: "Wireless Headphones",
    timecode: "00:12–00:38",
    screenTime: "26s",
    naturalness: 92,
    brandSafety: 96,
    complexity: "Low",
    rights: "Clear",
    estimatedValue: "$185,000",
    primary: true,
  },
  {
    id: "opp_horizons_rooftop_002",
    sceneId: "rooftop-reflection",
    category: "Mobile Devices",
    object: "Smartphone",
    timecode: "00:20–00:33",
    screenTime: "13s",
    naturalness: 78,
    brandSafety: 95,
    complexity: "Low",
    rights: "Clear",
    estimatedValue: "$74,000",
  },
  {
    id: "opp_horizons_rooftop_003",
    sceneId: "rooftop-reflection",
    category: "Smart Home",
    object: "Smart Speaker",
    timecode: "00:05–00:29",
    screenTime: "20s",
    naturalness: 74,
    brandSafety: 93,
    complexity: "Medium",
    rights: "Clear",
    estimatedValue: "$66,000",
  },
  {
    id: "opp_horizons_rooftop_004",
    sceneId: "rooftop-reflection",
    category: "Home / Beverage",
    object: "Coffee Mug",
    timecode: "00:28–00:41",
    screenTime: "11s",
    naturalness: 71,
    brandSafety: 94,
    complexity: "Medium",
    rights: "Review",
    estimatedValue: "$38,000",
  },
  {
    id: "opp_horizons_rooftop_005",
    sceneId: "rooftop-reflection",
    category: "Home / Lighting",
    object: "Table Lamp",
    timecode: "00:02–00:44",
    screenTime: "34s",
    naturalness: 58,
    brandSafety: 97,
    complexity: "High",
    rights: "Clear",
    estimatedValue: "$22,000",
  },
];

export const demoOpportunityDetails: Record<string, OpportunityDetail> = {
  opp_horizons_rooftop_001: {
    ...demoOpportunities[0],
    slug: "opp_horizons_rooftop_001",
    title: "Wireless Headphones Placement",
    description:
      "The character rests wireless headphones on the ledge as she reflects — a natural, product-supportive beat that does not touch plot, dialogue, or motivation. Stable framing, clean visibility, aspirational tone. A strong fit for premium consumer-audio and lifestyle-tech categories.",
    metrics: [
      { key: "Naturalness", value: "92", color: "green", barPercent: 92 },
      { key: "Brand safety", value: "96", color: "green", barPercent: 96 },
      { key: "Screen time", value: "26s", note: "of 32s scene" },
      { key: "Technical complexity", value: "Low", note: "already in frame" },
      { key: "Camera stability", value: "High", note: "locked-off" },
      { key: "Rights status", value: "Clear", color: "green", note: "configured territories" },
    ],
    compatibleCategories: ["Consumer audio", "Lifestyle tech", "Wearables", "Premium design"],
    territories: [
      { name: "United States", status: "Cleared" },
      { name: "Canada", status: "Cleared" },
      { name: "United Kingdom", status: "Cleared" },
      { name: "Germany", status: "Restricted" },
    ],
    clickhouseSignals: {
      comparableDeals: "14 in category",
      medianFee: "$171,500",
      categoryDemand: "High · rising",
    },
  },
};

export function getOpportunitiesForScene(sceneId: string): Opportunity[] {
  return demoOpportunities.filter((o) => o.sceneId === sceneId);
}

export function getOpportunityById(id: string): OpportunityDetail | undefined {
  return demoOpportunityDetails[id];
}

export const DEFAULT_OPPORTUNITY_ID = "opp_horizons_rooftop_001";

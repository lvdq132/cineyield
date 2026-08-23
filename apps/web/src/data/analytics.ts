import type {
  Agent,
  AgentTraceLine,
  AnalyticsStat,
  CategorySegment,
  ContentRevenue,
  PipelineStep,
  TopScene,
} from "@/lib/types";

/** @fixture Demo analytics — replace with GET /api/analytics */
export function getAnalyticsStats(approved: boolean): AnalyticsStat[] {
  const dealsCount = approved ? "19" : "18";
  const approvedRev = approved ? "$1.81M" : "$1.62M";

  return [
    { label: "Content scanned", value: "6 titles" },
    { label: "Opportunities", value: "342" },
    { label: "Qualified matches", value: "128" },
    { label: "Deals closed", value: dealsCount },
    { label: "Est. placement revenue", value: "$4.8M" },
    { label: "Approved revenue", value: approvedRev, color: "gold" },
    { label: "Time saved", value: "340 hrs", color: "green" },
    { label: "Approval cycle", value: "1.8 days" },
  ];
}

export const demoContentRevenue: ContentRevenue[] = [
  { key: "TV Series", value: "$1.9M", percent: 88 },
  { key: "Feature Film", value: "$1.2M", percent: 60 },
  { key: "Microdrama", value: "$820K", percent: 42 },
  { key: "YouTube / Creator", value: "$540K", percent: 28 },
  { key: "Social", value: "$310K", percent: 16 },
];

/** @fixture Demo category mix — replace with a live revenue-by-category aggregate */
export const demoCategorySegments: CategorySegment[] = [
  { label: "Consumer audio", color: "#3b82f6", pct: 34 },
  { label: "Mobile / devices", color: "#2563eb", pct: 28 },
  { label: "Smart home", color: "#1d4ed8", pct: 22 },
  { label: "Beverage / other", color: "#1e3a8a", pct: 16 },
];

export const demoTopScenes: TopScene[] = [
  {
    name: "Rooftop Reflection",
    show: "HORIZONS · S2E3",
    value: "$185K",
    gold: true,
    thumbGradient: "radial-gradient(circle at 40% 30%,#3a3050,#18121f)",
  },
  {
    name: "Coastal Drive",
    show: "Echoes of Tomorrow",
    value: "$142K",
    thumbGradient: "radial-gradient(circle at 60% 40%,#2a3a4a,#12181f)",
  },
  {
    name: "Sci-Fi Corridor",
    show: "North Line · S1E4",
    value: "$118K",
    thumbGradient: "radial-gradient(circle at 50% 50%,#453045,#191219)",
  },
  {
    name: "Night Market",
    show: "Second Chapter",
    value: "$96K",
    thumbGradient: "radial-gradient(circle at 30% 60%,#4a3030,#1f1414)",
  },
];

/** @fixture Demo agent orchestration — replace with GET /api/agents */
export const demoAgents: Agent[] = [
  {
    name: "Scene Agent",
    role: "Understand content & structure scenes",
    state: "Complete",
    kind: "ok",
    tool: "gemini · video.understand",
    latency: "1,240ms",
  },
  {
    name: "Market Agent",
    role: "Query commercial inventory in ClickHouse",
    state: "Complete",
    kind: "ok",
    tool: "mcp-clickhouse · query",
    latency: "45ms",
    hero: true,
  },
  {
    name: "Brand Agent",
    role: "Score semantic & audience fit",
    state: "Complete",
    kind: "ok",
    tool: "gemini · fit.score",
    latency: "820ms",
  },
  {
    name: "Rights Agent",
    role: "Apply territory / usage / exclusivity",
    state: "Pass",
    kind: "pass",
    tool: "rules.evaluate (deterministic)",
    latency: "12ms",
  },
  {
    name: "Creative Guardian",
    role: "Protect story integrity · can veto",
    state: "Pass",
    kind: "pass",
    tool: "gemini · narrative.guard",
    latency: "910ms",
  },
  {
    name: "Deal Agent",
    role: "Assemble structured proposal",
    state: "Ready",
    kind: "ready",
    tool: "deal.compose",
    latency: "8ms",
  },
];

export const demoPipeline: PipelineStep[] = [
  { label: "Ingest" },
  { label: "Understand" },
  { label: "Discover" },
  { label: "Match", active: true },
  { label: "Approve" },
  { label: "Activate" },
];

export const demoAgentTrace: AgentTraceLine[] = [
  { line: "POST mcp-clickhouse/tools/call → query" },
  { line: "SELECT campaign_id, brand_name, final_score" },
  { line: "FROM brand_campaigns WHERE category='consumer_audio'" },
  { line: "AND max_budget>=100000 AND has(territories,'US')" },
  { line: "ORDER BY final_score DESC → 27 rows · 45ms", dim: true },
];

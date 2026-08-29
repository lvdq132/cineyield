/** Demo fixture types — replace with API types from packages/shared-types later. */

export type ContentFormat =
  | "tv series"
  | "film"
  | "microdrama"
  | "youtube"
  | "social";

export type AnalysisStatus = "Analyzed" | "Analyzing" | "Queued" | "Failed";

export interface ContentProject {
  id: string;
  title: string;
  subtitle: string;
  format: ContentFormat;
  status: AnalysisStatus;
  scenes: string;
  opportunities: string;
  estimatedValue: string;
  updated: string;
  thumbnailGradient: string;
  /**
   * Destination for the card. Set from live data to the asset's first analyzed
   * scene. Undefined means nothing in this asset has been analyzed yet, and the
   * card renders as non-navigable rather than as a link into a dead end.
   */
  href?: string;
  /**
   * How many scenes of this asset the pipeline has actually analyzed, versus
   * how many the catalogue says exist. These are genuinely different numbers:
   * `content_assets.scene_count` is catalogue metadata (a series really does
   * have 312 scenes), while the `scenes` table only holds what Gemini has
   * processed. Showing the catalogue figure alone implies 312 clickable scenes
   * and invites a judge to ask for one we cannot open.
   */
  analyzedScenes?: number;
  totalScenes?: number;
}

export interface DetectedObject {
  label: string;
  category: string;
  confidence: number;
  isPrimary?: boolean;
}

export interface DetectionBox {
  label: string;
  confidence: number;
  x: number;
  y: number;
  width: number;
  height: number;
  primary?: boolean;
}

export interface Scene {
  id: string;
  projectId: string;
  projectTitle: string;
  episode: string;
  name: string;
  summary: string;
  brandSafety: number;
  narrativeWeight: string;
  mood: string;
  duration: string;
  currentTime: string;
  playerGradient: string;
  detectedObjects: DetectedObject[];
  detectionBoxes: DetectionBox[];
  frameUrl?: string;
  videoUrl?: string;
  frameTimeSeconds?: number;
  sourceDurationSeconds?: number;
}

export type RightsStatus = "Clear" | "Review";
export type Complexity = "Low" | "Medium" | "High";

export interface Opportunity {
  id: string;
  sceneId: string;
  category: string;
  object: string;
  timecode: string;
  screenTime: string;
  naturalness: number;
  brandSafety: number;
  complexity: Complexity;
  rights: RightsStatus;
  estimatedValue: string;
  primary?: boolean;
  placementZone?: string;
  placementNotes?: string;
}

export interface OpportunityMetric {
  key: string;
  value: string;
  color?: "green" | "ink";
  barPercent?: number;
  note?: string;
}

export interface OpportunityDetail extends Opportunity {
  slug: string;
  title: string;
  description: string;
  metrics: OpportunityMetric[];
  compatibleCategories: string[];
  territories: { name: string; status: "Cleared" | "Restricted" }[];
  clickhouseSignals: {
    comparableDeals: string;
    medianFee: string;
    categoryDemand: string;
  };
}

export interface CampaignMatch {
  id: string;
  brand: string;
  line: string;
  score: number;
  blocked?: boolean;
  statusLabel?: string;
}

export interface TopMatch {
  brand: string;
  product: string;
  campaign: string;
  score: number;
  budget: string;
  visibility: string;
  territories: string;
  exclusivity: string;
}

export interface MatchBreakdown {
  key: string;
  value: number;
}

export interface Guardrail {
  name: string;
  detail: string;
  mark: string;
  status: "PASS" | "REVIEW";
  statusColor: "green" | "amber";
}

export interface ProposalTerm {
  label: string;
  value: string;
  highlight?: boolean;
  /** True when this term is illustrative deal-template text, not sourced from the backend. */
  modelled?: boolean;
}

export interface Proposal {
  id: string;
  brandName: string;
  campaignName: string;
  brandBrief: string;
  sceneTitle: string;
  sceneEpisode: string;
  sceneDetail: string;
  sceneDescription: string;
  placementFee: string;
  terms: ProposalTerm[];
  guardrails: Guardrail[];
}

export interface AuditEvent {
  text: string;
  who: string;
  time: string;
  dotColor: "gold" | "green";
}

export interface Agent {
  name: string;
  role: string;
  state: string;
  kind: "ok" | "pass" | "ready";
  tool: string;
  latency: string;
  hero?: boolean;
}

export interface AgentTraceLine {
  line: string;
  dim?: boolean;
}

export interface PipelineStep {
  label: string;
  active?: boolean;
}

export interface AnalyticsStat {
  label: string;
  value: string;
  color?: "ink" | "gold" | "green" | "amber";
  /** True when this figure is a modelled/illustrative projection rather than a live aggregate. */
  modelled?: boolean;
}

export interface ContentRevenue {
  key: string;
  value: string;
  percent: number;
}

export interface TopScene {
  name: string;
  show: string;
  value: string;
  gold?: boolean;
  thumbGradient: string;
}

export interface CategorySegment {
  label: string;
  color: string;
  /** Share of the donut, 0-100. Segments in a set should sum to 100. */
  pct: number;
}

export interface AnalyzeStep {
  label: string;
  threshold: number;
}

export interface LibraryStat {
  label: string;
  value: string;
  color?: "ink" | "amber";
}

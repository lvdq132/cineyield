import type { ContentProject, LibraryStat } from "@/lib/types";

/** @fixture Demo content catalog — replace with GET /api/content */
export const DEMO_ESTIMATED_VALUE = "$4.8M";

export const demoLibraryStats: LibraryStat[] = [
  { label: "Scenes analyzed", value: "1,284" },
  { label: "Opportunities", value: "342" },
  { label: "Active deals", value: "18" },
  { label: "Approvals pending", value: "5", color: "amber" },
];

export function getLibraryStats(approved: boolean): LibraryStat[] {
  return demoLibraryStats.map((stat) =>
    stat.label === "Active deals"
      ? { ...stat, value: approved ? "19" : "18" }
      : stat,
  );
}

export const demoCatalog: ContentProject[] = [
  {
    id: "horizons",
    title: "HORIZONS",
    subtitle: "Sci-Fi Drama Series · S2",
    format: "tv series",
    status: "Analyzed",
    scenes: "312",
    opportunities: "47",
    estimatedValue: "$2.84M",
    updated: "2h ago",
    thumbnailGradient:
      "radial-gradient(120% 100% at 30% 20%,#3a3050,#221d2e 55%,#0d0b0f)",
  },
  {
    id: "echoes",
    title: "Echoes of Tomorrow",
    subtitle: "Feature Film",
    format: "film",
    status: "Analyzed",
    scenes: "88",
    opportunities: "12",
    estimatedValue: "$960K",
    updated: "1d ago",
    thumbnailGradient:
      "radial-gradient(120% 100% at 70% 30%,#2a3a4a,#1a222c 55%,#0b0d10)",
  },
  {
    id: "second-chapter",
    title: "Second Chapter",
    subtitle: "Microdrama",
    format: "microdrama",
    status: "Analyzing",
    scenes: "54",
    opportunities: "—",
    estimatedValue: "—",
    updated: "live",
    thumbnailGradient:
      "radial-gradient(120% 100% at 50% 40%,#4a3030,#2a1e1e 55%,#0f0b0a)",
  },
  {
    id: "frame-by-frame",
    title: "Frame by Frame",
    subtitle: "Creator Series",
    format: "youtube",
    status: "Analyzed",
    scenes: "31",
    opportunities: "9",
    estimatedValue: "$120K",
    updated: "3d ago",
    thumbnailGradient:
      "radial-gradient(120% 100% at 40% 30%,#3a3a2a,#22221a 55%,#0d0d0a)",
  },
  {
    id: "urban-pulse",
    title: "Urban Pulse",
    subtitle: "Social Clips",
    format: "social",
    status: "Queued",
    scenes: "—",
    opportunities: "—",
    estimatedValue: "—",
    updated: "—",
    thumbnailGradient:
      "radial-gradient(120% 100% at 60% 40%,#2c3238,#191d20 55%,#0a0c0d)",
  },
  {
    id: "north-line",
    title: "North Line",
    subtitle: "TV Drama",
    format: "tv series",
    status: "Analyzed",
    scenes: "120",
    opportunities: "19",
    estimatedValue: "$780K",
    updated: "5d ago",
    thumbnailGradient:
      "radial-gradient(120% 100% at 35% 25%,#453045,#241e24 55%,#0e0b0e)",
  },
];

export function getContentById(id: string): ContentProject | undefined {
  return demoCatalog.find((c) => c.id === id);
}

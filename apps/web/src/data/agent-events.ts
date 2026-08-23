import type { AnalyzeStep, AuditEvent } from "@/lib/types";

/** @fixture Demo analyze flow steps */
export const demoAnalyzeSteps: AnalyzeStep[] = [
  { label: "Uploading source", threshold: 8 },
  { label: "Storing to Cloud Storage", threshold: 24 },
  { label: "Segmenting scenes", threshold: 44 },
  { label: "Extracting objects (Gemini)", threshold: 66 },
  { label: "Writing scene intelligence (ClickHouse)", threshold: 86 },
  { label: "Complete", threshold: 100 },
];

export const ANALYZE_SOURCE = "HORIZONS · Rooftop Reflection.mp4";
export const ANALYZE_TARGET_SCENE = "rooftop-reflection";

/** @fixture Base audit trail — append approval event when approved */
export const demoAuditBase: AuditEvent[] = [
  {
    text: "Scene analyzed · 6 objects, 5 opportunities",
    who: "Scene Agent",
    time: "00:00",
    dotColor: "gold",
  },
  {
    text: "ClickHouse queried · 27 campaigns, 6 ranked",
    who: "Market Agent",
    time: "00:01",
    dotColor: "green",
  },
  {
    text: "Rights Pass (3/4) · Creative Guardian Pass",
    who: "Rights + Guardian",
    time: "00:02",
    dotColor: "green",
  },
  {
    text: "Proposal composed · $185,000 · 12mo",
    who: "Deal Agent",
    time: "00:02",
    dotColor: "gold",
  },
];

export function getAuditTrail(approved: boolean): AuditEvent[] {
  if (!approved) return demoAuditBase;
  return [
    ...demoAuditBase,
    {
      text: "Placement APPROVED",
      who: "Maya Reyes (Producer)",
      time: "just now",
      dotColor: "green",
    },
  ];
}

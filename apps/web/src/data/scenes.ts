import type { Scene } from "@/lib/types";

/** @fixture Demo scene data — replace with GET /api/scenes/:id */
export const demoScenes: Record<string, Scene> = {
  "rooftop-reflection": {
    id: "rooftop-reflection",
    projectId: "horizons",
    projectTitle: "HORIZONS",
    episode: "S2E3",
    name: "Rooftop Reflection",
    summary:
      "A protagonist finishes a long day and looks over a futuristic city at dusk. Reflective, aspirational, premium and technology-forward — a natural, low-distraction context for lifestyle tech.",
    brandSafety: 96,
    narrativeWeight: "High",
    mood: "Dusk",
    duration: "00:44",
    currentTime: "00:12",
    playerGradient:
      "radial-gradient(130% 100% at 50% 14%,#3a3050 0%,#221d2e 44%,#0d0b0f 100%)",
    detectedObjects: [
      { label: "Wireless Headphones", category: "Consumer audio", confidence: 94, isPrimary: true },
      { label: "Smartphone", category: "Mobile devices", confidence: 92 },
      { label: "Coffee Mug", category: "Home / beverage", confidence: 89 },
      { label: "Smart Speaker", category: "Smart home", confidence: 86 },
      { label: "Table Lamp", category: "Home / lighting", confidence: 83 },
      { label: "Backpack", category: "Accessories", confidence: 81 },
    ],
    detectionBoxes: [
      { label: "Wireless Headphones", confidence: 94, x: 30, y: 48, width: 15, height: 16, primary: true },
      { label: "Smartphone", confidence: 92, x: 58, y: 60, width: 9, height: 13 },
      { label: "Smart Speaker", confidence: 86, x: 74, y: 42, width: 11, height: 24 },
    ],
  },
};

export const DEFAULT_SCENE_ID = "rooftop-reflection";

export function getSceneById(id: string): Scene | undefined {
  return demoScenes[id];
}

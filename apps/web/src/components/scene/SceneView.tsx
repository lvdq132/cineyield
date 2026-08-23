"use client";

import Link from "next/link";
import type { Opportunity, Scene } from "@/lib/types";
import {
  Breadcrumb,
  NaturalnessChip,
  RightsChip,
  SectionLabel,
} from "@/components/ui";
import { DEFAULT_OPPORTUNITY_ID } from "@/data/opportunities";
import { DataSourceNotice } from "@/components/ui/DataSourceNotice";
import type { DataSource } from "@/lib/data-source";

interface SceneViewProps {
  scene: Scene;
  opportunities: Opportunity[];
  dataSource?: DataSource;
}

export function SceneView({ scene, opportunities, dataSource = "live" }: SceneViewProps) {
  return (
    <div className="animate-cyrise">
      <Breadcrumb
        items={[
          { label: "Studio Library", href: "/library" },
          { label: `${scene.projectTitle} · ${scene.episode}` },
          { label: scene.name },
        ]}
      />

      <DataSourceNotice source={dataSource} />

      <div className="mb-5 grid grid-cols-1 gap-5 lg:grid-cols-[1fr_316px]">
        <SceneVideoPanel scene={scene} />
        <DetectedObjectsPanel scene={scene} />
      </div>

      <OpportunityTable opportunities={opportunities} />
    </div>
  );
}

function SceneVideoPanel({ scene }: { scene: Scene }) {
  return (
    <div className="overflow-hidden rounded bg-panel">
      <div
        className="relative aspect-video overflow-hidden"
        style={{ background: scene.playerGradient }}
      >
        <div className="absolute inset-0 bg-gradient-to-t from-[#0d0b0f] from-0% to-transparent to-[46%]" />
        <div className="absolute left-1/2 top-[56%] h-[66px] w-8 -translate-x-1/2 -translate-y-1/2 rounded-b-[3px] rounded-t-xl bg-[#100d15]" />

        {scene.detectionBoxes.map((box) => (
          <div
            key={box.label}
            className="absolute"
            style={{
              left: `${box.x}%`,
              top: `${box.y}%`,
              width: `${box.width}%`,
              height: `${box.height}%`,
              border: box.primary
                ? "1.5px solid var(--color-gold)"
                : "1px solid rgba(99,102,241,0.5)",
              background: box.primary ? "rgba(99,102,241,0.08)" : "transparent",
            }}
          >
            <span
              className="absolute -left-px -top-[19px] whitespace-nowrap px-1.5 py-0.5 font-mono text-[9.5px]"
              style={{
                background: box.primary ? "var(--color-gold)" : "rgba(13,11,9,0.85)",
                color: box.primary ? "#ffffff" : "#e9ddc4",
              }}
            >
              {box.label} · {box.confidence}
            </span>
          </div>
        ))}

        <div className="absolute left-4 top-3.5 flex items-center gap-2 rounded bg-[rgba(13,11,9,0.7)] px-2.5 py-1">
          <span className="h-1.5 w-1.5 animate-cypulse rounded-full bg-gold" />
          <span className="font-mono text-[10.5px] text-[#e9ddc4]">
            gemini · scene understanding
          </span>
        </div>

        <div className="absolute bottom-0 left-0 right-0 flex items-center gap-3.5 px-4 py-3.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[rgba(255,255,255,0.14)]">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="#fff" aria-hidden>
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <div className="relative h-[3px] flex-1 bg-[rgba(255,255,255,0.18)]">
            <div className="absolute left-0 top-0 h-full w-[34%] bg-gold" />
            <div className="absolute left-[34%] top-[-3px] h-[9px] w-[9px] rounded-full bg-white" />
          </div>
          <span className="font-mono text-[11.5px] text-[#cfc9bd]">
            {scene.currentTime} / {scene.duration}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-[22px] px-[18px] py-[17px]">
        <div className="min-w-[230px] flex-1">
          <SectionLabel>SCENE SUMMARY</SectionLabel>
          <p className="mt-1.5 text-[13px] leading-[1.55] text-pretty text-ink">
            {scene.summary}
          </p>
        </div>
        <div className="flex flex-none gap-[22px]">
          <MetricBlock value={String(scene.brandSafety)} label="Brand safety" mono />
          <MetricBlock value={scene.narrativeWeight} label="Narrative weight" gold />
          <MetricBlock value={scene.mood} label="Mood" />
        </div>
      </div>
    </div>
  );
}

function MetricBlock({
  value,
  label,
  mono,
  gold,
}: {
  value: string;
  label: string;
  mono?: boolean;
  gold?: boolean;
}) {
  return (
    <div>
      <div
        className={`${
          mono
            ? "font-mono text-[22px] text-green"
            : gold
              ? "text-[24px] font-bold leading-none tracking-[-0.02em] text-gold"
              : "text-[24px] font-bold leading-none tracking-[-0.02em] text-ink"
        }`}
      >
        {value}
      </div>
      <div className="mt-0.5 text-[10px] text-ink3">{label}</div>
    </div>
  );
}

function DetectedObjectsPanel({ scene }: { scene: Scene }) {
  return (
    <div className="flex flex-col rounded bg-panel p-[18px]">
      <div className="mb-3.5 flex items-center justify-between">
        <SectionLabel>DETECTED OBJECTS</SectionLabel>
        <span className="font-mono text-[11px] text-ink3">
          {scene.detectedObjects.length} found
        </span>
      </div>
      <div className="flex flex-1 flex-col">
        {scene.detectedObjects.map((obj) => (
          <div
            key={obj.label}
            className="flex items-center gap-3 border-t border-line py-[11px]"
          >
            <span
              className="h-6 w-[3px] flex-none"
              style={{
                background: obj.isPrimary ? "var(--color-gold)" : "#1e1e22",
              }}
            />
            <div className="flex-1">
              <div className="text-[12.5px] font-medium text-ink">{obj.label}</div>
              <div className="text-[10.5px] text-ink3">{obj.category}</div>
            </div>
            <div className="font-mono text-[12.5px] text-ink2">{obj.confidence}</div>
          </div>
        ))}
      </div>
      <div className="mt-3.5 rounded bg-well p-3.5">
        <div className="text-[9.5px] font-semibold tracking-[1.2px] text-gold">
          TOP RECOMMENDATION
        </div>
        <p className="mt-1.5 text-[12.5px] leading-[1.45] text-ink">
          Wireless headphones — highest naturalness and screen time. Detected ≠
          sellable until contextually scored.
        </p>
      </div>
    </div>
  );
}

function OpportunityTable({ opportunities }: { opportunities: Opportunity[] }) {
  return (
    <div className="overflow-hidden rounded bg-panel">
      <div className="flex items-baseline justify-between px-[22px] pb-3.5 pt-[18px]">
        <h2 className="text-[20px] font-bold tracking-[-0.02em] text-ink">
          Placement Opportunities
        </h2>
        <span className="font-mono text-[11px] text-ink3">
          scored from context, not raw detection
        </span>
      </div>

      <div className="grid grid-cols-[1.6fr_1fr_0.7fr_0.9fr_0.9fr_0.8fr_0.9fr_0.9fr_34px] gap-0 border-b border-line px-[22px] py-2 text-[9.5px] font-semibold uppercase tracking-[1px] text-ink3">
        <div>Opportunity</div>
        <div>Timecode</div>
        <div>Screen</div>
        <div>Naturalness</div>
        <div>Brand safe</div>
        <div>Complexity</div>
        <div>Rights</div>
        <div className="text-right">Est. value</div>
        <div />
      </div>

      {opportunities.map((opp) => (
        <Link
          key={opp.id}
          href={`/opportunities/${opp.id}`}
          className={`grid cursor-pointer grid-cols-[1.6fr_1fr_0.7fr_0.9fr_0.9fr_0.8fr_0.9fr_0.9fr_34px] gap-0 border-t border-line px-[22px] py-[13px] transition-colors hover:bg-[rgba(255,255,255,0.03)] ${
            opp.primary ? "bg-[rgba(99,102,241,0.06)]" : ""
          }`}
        >
          <div className="flex flex-col">
            <span className="text-[13px] font-semibold text-ink">{opp.category}</span>
            <span className="text-[11px] text-ink3">{opp.object}</span>
          </div>
          <div className="self-center font-mono text-xs text-ink2">{opp.timecode}</div>
          <div className="self-center font-mono text-xs text-ink2">{opp.screenTime}</div>
          <div className="self-center">
            <NaturalnessChip value={opp.naturalness} />
          </div>
          <div className="self-center font-mono text-[12.5px] text-ink">
            {opp.brandSafety}
          </div>
          <div className="self-center text-xs text-ink2">{opp.complexity}</div>
          <div className="self-center">
            <RightsChip status={opp.rights} />
          </div>
          <div className="self-center text-right font-mono text-[13px] font-bold text-gold">
            {opp.estimatedValue}
          </div>
          <div className="self-center text-right text-ink3">›</div>
        </Link>
      ))}
    </div>
  );
}

export { DEFAULT_OPPORTUNITY_ID };

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
          {
            label: scene.episode
              ? `${scene.projectTitle} · ${scene.episode}`
              : scene.projectTitle,
          },
          { label: scene.name },
        ]}
      />

      <div className="mb-8 grid grid-cols-1 gap-5 border-b border-line pb-7 md:grid-cols-[1fr_420px] md:items-end">
        <div><span className="font-mono text-[9px] font-bold uppercase tracking-[0.12em] text-gold">Scene intelligence / {scene.currentTime}</span><h1 className="mt-4 text-[clamp(42px,5vw,72px)] font-medium leading-[0.9] tracking-[-0.06em] text-ink">{scene.name}.</h1></div>
        <p className="m-0 text-[15px] leading-[1.6] text-ink2">One analyzed frame, its contextual signals, and the sponsor opportunities qualified from the complete scene.</p>
      </div>

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
    <div className="overflow-hidden border border-line bg-panel">
      <div
        className="relative aspect-video overflow-hidden"
        style={{ backgroundImage: "linear-gradient(180deg,rgba(9,10,11,.1),rgba(9,10,11,.66)),url('/cineyield-rooftop-hero.jpg')", backgroundSize: "cover", backgroundPosition: "center" }}
      >
        <div className="absolute left-4 top-4 flex items-center gap-3 border border-[rgba(242,240,234,.24)] bg-[rgba(9,10,11,.76)] px-3 py-2">
          <span className="h-1.5 w-1.5 bg-gold" />
          <span className="font-mono text-[9px] font-bold uppercase tracking-[0.1em] text-ink">Gemini scene intelligence</span>
        </div>
        <div className="absolute bottom-4 right-4 border border-[rgba(242,240,234,.24)] bg-[rgba(9,10,11,.76)] px-3 py-2 font-mono text-[10px] text-ink">
          Frame {scene.currentTime}
        </div>
      </div>

      <div className="grid grid-cols-1 border-t border-line lg:grid-cols-[1.35fr_.65fr]">
        <div className="min-w-[230px] p-5 lg:p-6">
          <SectionLabel>SCENE SUMMARY</SectionLabel>
          <p className="mt-4 max-w-[720px] text-[15px] leading-[1.6] text-pretty text-ink2">
            {scene.summary}
          </p>
        </div>
        <div className="grid grid-cols-3 border-t border-line lg:border-l lg:border-t-0">
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
    <div className="flex min-h-[118px] flex-col justify-end border-r border-line p-4 last:border-r-0">
      <div
        className={`${
          mono
            ? "text-[28px] font-semibold leading-none tracking-[-0.04em] text-green"
            : gold
              ? "text-[28px] font-semibold leading-none tracking-[-0.04em] text-gold"
              : "text-[28px] font-semibold leading-none tracking-[-0.04em] text-ink"
        }`}
      >
        {value}
      </div>
      <div className="mt-3 text-[9px] font-bold uppercase tracking-[0.07em] text-ink3">{label}</div>
    </div>
  );
}

function DetectedObjectsPanel({ scene }: { scene: Scene }) {
  const topObject =
    scene.detectedObjects.find((o) => o.isPrimary) ?? scene.detectedObjects[0];
  return (
    <div className="flex flex-col border border-line bg-panel p-5">
      <div className="mb-3.5 flex items-center justify-between">
        <SectionLabel>SCENE SIGNALS</SectionLabel>
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
      <div className="mt-4 border-t border-line pt-4">
        <div className="text-[9.5px] font-semibold tracking-[1.2px] text-gold">
          TOP SPONSOR FIT
        </div>
        <p className="mt-1.5 text-[12.5px] leading-[1.45] text-ink">
          {topObject
            ? `${topObject.label} leads on naturalness and screen time. The producer still controls whether the opportunity advances.`
            : "No sponsor-ready placement has been qualified yet."}
        </p>
      </div>
    </div>
  );
}

function OpportunityTable({ opportunities }: { opportunities: Opportunity[] }) {
  return (
    <div className="overflow-hidden border border-line bg-panel">
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
            opp.primary ? "bg-[rgba(241,93,59,0.06)]" : ""
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

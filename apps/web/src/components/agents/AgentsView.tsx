import type { Agent, AgentTraceLine, PipelineStep } from "@/lib/types";
import { SectionLabel } from "@/components/ui";
import { DataSourceNotice } from "@/components/ui/DataSourceNotice";
import type { DataSource } from "@/lib/data-source";

interface AgentsViewProps {
  agents: Agent[];
  pipeline: PipelineStep[];
  trace: AgentTraceLine[];
  isLive?: boolean;
  eventCount?: number;
  dataSource?: DataSource;
}

export function AgentsView({
  agents,
  pipeline,
  trace,
  isLive,
  eventCount,
  dataSource = "live",
}: AgentsViewProps) {
  return (
    <div className="animate-cyrise">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="m-0 text-[30px] font-bold leading-[1.05] tracking-[-0.02em] text-ink">
            Agent Orchestration
          </h1>
          <p className="mt-[7px] text-[13px] text-ink2">
            Six agents. One deterministic workflow. Every tool call observable.{" "}
            {isLive && eventCount != null && (
              <span className="text-green">{eventCount} real events from ClickHouse.</span>
            )}
          </p>
        </div>
        <ServiceIndicators />
      </div>

      <DataSourceNotice source={dataSource} />

      <PipelineStrip steps={pipeline} />

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_344px]">
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2">
          {agents.map((agent) => (
            <AgentCard key={agent.name} agent={agent} />
          ))}
        </div>
        <AgentTracePanel trace={trace} isLive={isLive} eventCount={eventCount} />
      </div>
    </div>
  );
}

function ServiceIndicators() {
  const services = [
    { label: "gemini", live: true, color: "green" },
    { label: "clickhouse-mcp", live: true, pulse: true, color: "green" },
    { label: "cloud-storage", live: true, color: "green" },
    { label: "parallel · off", live: false, color: "ink3" },
  ] as const;

  return (
    <div className="flex flex-wrap gap-[18px]">
      {services.map((s) => (
        <div key={s.label} className="flex items-center gap-1.5">
          <span
            className={`h-1.5 w-1.5 rounded-full bg-${s.color} ${
              "pulse" in s && s.pulse ? "animate-cypulse" : ""
            }`}
            style={{
              background:
                s.color === "green"
                  ? "var(--color-green)"
                  : "var(--color-ink3)",
            }}
          />
          <span
            className={`font-mono text-[11.5px] ${
              s.live ? (s.color === "green" ? "text-green" : "text-ink2") : "text-ink3"
            }`}
          >
            {s.label}
          </span>
        </div>
      ))}
    </div>
  );
}

function PipelineStrip({ steps }: { steps: PipelineStep[] }) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 rounded bg-panel px-5 py-4">
      {steps.map((step, i) => (
        <span key={step.label} className="flex items-center gap-2">
          <span
            className={`whitespace-nowrap rounded-[2px] px-[13px] py-[7px] text-[11.5px] font-semibold ${
              step.active
                ? "bg-[rgba(99,102,241,0.14)] text-gold"
                : "bg-well text-ink2"
            }`}
          >
            {step.label}
          </span>
          {i < steps.length - 1 && (
            <span className="font-mono text-sm text-ink3">→</span>
          )}
        </span>
      ))}
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const stateChipStyles: Record<Agent["kind"], string> = {
    ok: "bg-[rgba(126,190,150,0.14)] text-green",
    pass: "bg-[rgba(126,190,150,0.14)] text-green",
    ready: "bg-[rgba(99,102,241,0.14)] text-gold",
  };

  return (
    <div
      className={`rounded bg-panel p-[17px] ${
        agent.hero ? "border-l-[3px] border-l-green" : "border-l-[3px] border-l-transparent"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke={agent.hero ? "var(--color-green)" : "var(--color-gold)"}
            strokeWidth="1.8"
            aria-hidden
          >
            <circle cx="12" cy="12" r="3.2" />
            <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
          </svg>
          <span className="text-[17px] font-normal tracking-[-0.02em] text-ink">
            {agent.name}
          </span>
        </div>
        <span
          className={`rounded-[2px] px-2 py-0.5 text-[9.5px] font-semibold tracking-[0.5px] ${stateChipStyles[agent.kind]}`}
        >
          {agent.state}
        </span>
      </div>
      <div className="mt-2 text-xs text-ink2">{agent.role}</div>
      <div className="mt-[13px] flex items-center gap-2 rounded bg-well px-[11px] py-2">
        <svg
          width="11"
          height="11"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--color-ink3)"
          strokeWidth="2"
          aria-hidden
        >
          <path d="M8 6 3 12l5 6M16 6l5 6-5 6" />
        </svg>
        <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap font-mono text-[11px] text-ink2">
          {agent.tool}
        </span>
        <span className="font-mono text-[11px] text-ink3">{agent.latency}</span>
      </div>
    </div>
  );
}

function AgentTracePanel({ trace, isLive, eventCount }: { trace: AgentTraceLine[]; isLive?: boolean; eventCount?: number }) {
  return (
    <div className="self-start rounded border-l-[3px] border-l-green bg-panel p-[22px]">
      <div className="mb-1 flex items-center gap-2">
        <span className="h-[7px] w-[7px] animate-cypulse rounded-full bg-green" />
        <span className="text-[18px] font-bold tracking-[-0.02em] text-green">
          Runtime event
        </span>
      </div>
      <div className="mb-4 font-mono text-[11px] text-ink2">
        market-agent → mcp-clickhouse → query
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3">
        <div className="rounded bg-well p-3">
          <div className="text-[10.5px] text-ink3">{isLive ? "Agent events" : "Rows returned"}</div>
          <div className="font-mono text-[20px] font-bold text-ink">{isLive && eventCount != null ? eventCount : 27}</div>
        </div>
        <div className="rounded bg-well p-3">
          <div className="text-[10.5px] text-ink3">Source</div>
          <div className={`font-mono text-[14px] font-bold ${isLive ? "text-green" : "text-ink2"}`}>{isLive ? "ClickHouse" : "45ms · fixture"}</div>
        </div>
      </div>

      <SectionLabel>SANITIZED TOOL TRACE</SectionLabel>
      <div className="mt-2 overflow-x-auto rounded bg-well p-[13px] font-mono text-[11px] leading-[1.7] text-[#8db99a]">
        {trace.map((line) => (
          <div
            key={line.line}
            className={line.dim ? "mt-[5px] text-[#5f8a6c]" : ""}
          >
            {line.line}
          </div>
        ))}
      </div>
    </div>
  );
}

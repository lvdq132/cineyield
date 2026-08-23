import { AgentsView } from "@/components/agents/AgentsView";
import { demoAgents, demoAgentTrace, demoPipeline } from "@/data/analytics";
import type { AgentTraceLine } from "@/lib/types";

import { IS_CONTEST_MODE as CONTEST_MODE } from "@/lib/contest-mode";
import { dataSourceFor } from "@/lib/data-source";
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface ApiAgentEvent {
  event_id: string;
  agent_name: string;
  kind: string;
  tool_name?: string;
  summary: string;
  latency_ms?: number;
  success: boolean;
  occurred_at: string;
}

function eventsToTrace(events: ApiAgentEvent[]): AgentTraceLine[] {
  if (events.length === 0) return demoAgentTrace;
  return events.slice(0, 8).flatMap((ev) => [
    { line: `${ev.agent_name} → ${ev.tool_name ?? ev.kind}` },
    { line: ev.summary, dim: true },
  ]);
}

async function fetchAgentEvents(): Promise<{ events: ApiAgentEvent[]; count: number } | null> {
  if (!API_BASE) return null;
  try {
    const res = await fetch(`${API_BASE}/api/v1/agents/events?limit=20`, {
      cache: "no-store",
    });
    if (!res.ok) {
      if (CONTEST_MODE) throw new Error(`Agent events API returned ${res.status}`);
      return null;
    }
    return res.json() as Promise<{ events: ApiAgentEvent[]; count: number }>;
  } catch (err) {
    if (CONTEST_MODE) throw err;
    return null;
  }
}

export default async function AgentsPage() {
  const liveEvents = await fetchAgentEvents();
  const trace = liveEvents ? eventsToTrace(liveEvents.events) : demoAgentTrace;
  const dataSource = dataSourceFor(Boolean(API_BASE), liveEvents !== null);

  return (
    <AgentsView
      agents={demoAgents}
      pipeline={demoPipeline}
      trace={trace}
      isLive={liveEvents !== null}
      eventCount={liveEvents?.count}
      dataSource={dataSource}
    />
  );
}

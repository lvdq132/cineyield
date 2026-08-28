"use client";

import { ArrowRight, Check, Loader2 } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import type { CampaignMatch, MatchBreakdown, TopMatch } from "@/lib/types";
import { Breadcrumb } from "@/components/ui";
import { DEFAULT_DEAL_ID } from "@/data/proposals";
import { ApiError, opportunities as oppsApi } from "@/lib/api-client";
import { DataSourceNotice } from "@/components/ui/DataSourceNotice";
import type { DataSource } from "@/lib/data-source";

interface MarketplaceViewProps {
  topMatch: TopMatch;
  matches: CampaignMatch[];
  breakdown: MatchBreakdown[];
  opportunityId?: string;
  topCampaignId?: string;
  totalScanned?: number;
  rankedCount?: number;
  mcpLatencyMs?: number;
  dataSource?: DataSource;
}

export function MarketplaceView({
  topMatch,
  matches,
  breakdown,
  opportunityId,
  topCampaignId,
  totalScanned,
  rankedCount,
  mcpLatencyMs,
  dataSource = "live",
}: MarketplaceViewProps) {
  return (
    <div className="animate-cyrise">
      <Breadcrumb
        items={[
          { label: "Opportunity", href: "/opportunities/opp_horizons_rooftop_001" },
          { label: "Brand Matches" },
        ]}
      />

      <div className="mb-8 grid grid-cols-1 gap-5 border-b border-line pb-7 md:grid-cols-[1fr_420px] md:items-end">
        <div><span className="font-mono text-[9px] font-bold uppercase tracking-[0.12em] text-gold">Sponsor demand / Ranked live</span><h1 className="mt-4 text-[clamp(42px,5vw,72px)] font-medium leading-[0.9] tracking-[-0.06em] text-ink">Campaign matches.</h1></div>
        <p className="m-0 text-[15px] leading-[1.6] text-ink2">Qualified campaigns ranked against narrative fit, rights, timing, budget, and producer-defined constraints.</p>
      </div>

      <DataSourceNotice source={dataSource} />

      <div className="mb-5 flex items-center gap-2.5 border-y border-line py-[11px]">
        <Check size={15} stroke="var(--color-green)" strokeWidth={2} aria-hidden />
        <span className="font-mono text-xs text-ink2">
          <span className="text-green">market-agent</span> queried clickhouse-mcp ·{" "}
          <span className="text-ink">{totalScanned ?? 27} campaigns scanned</span>{" "}
          · {rankedCount ?? matches.length + 1} ranked
          {mcpLatencyMs != null ? ` · ${mcpLatencyMs}ms` : " · 45ms"}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_336px]">
        <div className="flex flex-col gap-3.5">
          <TopMatchCard match={topMatch} opportunityId={opportunityId} campaignId={topCampaignId} />
          {matches.map((m) => (
            <MatchCard key={m.id} match={m} />
          ))}
        </div>

        <MatchBreakdownPanel breakdown={breakdown} score={topMatch.score} />
      </div>
    </div>
  );
}

function TopMatchCard({ match, opportunityId, campaignId }: { match: TopMatch; opportunityId?: string; campaignId?: string }) {
  const router = useRouter();
  const [proposing, setProposing] = useState(false);
  const [proposeError, setProposeError] = useState<string | null>(null);

  async function handleOpenProposal() {
    if (!(opportunityId && campaignId)) {
      // No opportunity/campaign context at all (e.g. fixture-mode page load
      // never got real ids) — this is the same as the API not being
      // configured, so the fixture deal is a legitimate demo destination.
      router.push(`/deals/${DEFAULT_DEAL_ID}`);
      return;
    }

    setProposing(true);
    setProposeError(null);
    try {
      const result = await oppsApi.propose(opportunityId, campaignId);
      router.push(`/deals/${result.proposal_id}`);
    } catch (err) {
      if (err instanceof ApiError && err.code === "API_NOT_CONFIGURED") {
        // Legitimate offline demo mode — no live API configured, so the
        // fixture deal is the disclosed demo destination, not a fake result.
        setProposing(false);
        router.push(`/deals/${DEFAULT_DEAL_ID}`);
        return;
      }
      // A configured API that failed must surface a real error — never
      // silently land on the fixture deal and imply success. See
      // DealView's approveError for the same pattern.
      const msg = err instanceof Error ? err.message : String(err);
      setProposing(false);
      setProposeError(msg);
    }
  }

  return (
    <div className="relative rounded bg-panel border-l-[3px] border-l-gold p-6">
      <div className="absolute right-6 top-6 text-[9.5px] font-semibold tracking-[1.4px] text-gold">
        TOP MATCH
      </div>
      <div className="flex items-start gap-[18px]">
        <div className="flex h-[52px] w-[52px] flex-none items-center justify-center rounded bg-[#1e1e22] text-[26px] font-bold tracking-[-0.02em] text-gold">
          A
        </div>
        <div className="flex-1">
          <div className="text-[24px] font-bold leading-[1.1] tracking-[-0.02em] text-ink">
            {match.brand}
          </div>
          <div className="mt-1 text-[12.5px] text-ink2">
            {match.product} · Campaign &ldquo;{match.campaign}&rdquo;
          </div>
        </div>
        <div className="mr-14 flex-none text-center">
          <ScoreRing score={match.score} />
          <div className="mt-0.5 text-[10px] text-ink3">match</div>
        </div>
      </div>

      <div className="mt-[22px] grid grid-cols-2 gap-3.5 border-t border-line pt-5 sm:grid-cols-4">
        <MetaItem label="Budget" value={match.budget} />
        <MetaItem label="Visibility" value={match.visibility} />
        <MetaItem label="Territories" value={match.territories} />
        <MetaItem label="Exclusivity" value={match.exclusivity} />
      </div>

      <button
        type="button"
        onClick={handleOpenProposal}
        disabled={proposing}
        className="mt-[22px] inline-flex cursor-pointer items-center gap-2 rounded bg-gold px-5 py-[11px] text-[13.5px] font-bold text-white transition-[filter] hover:brightness-110 disabled:opacity-60"
      >
        {proposing ? (
          <Loader2 size={15} strokeWidth={2.4} className="animate-spin" aria-hidden />
        ) : (
          <ArrowRight size={15} strokeWidth={2.4} aria-hidden />
        )}
        {proposing ? "Creating proposal…" : "Open proposal"}
      </button>

      {proposeError && (
        <div className="mt-3 flex animate-cyrise items-center gap-3 rounded border-l-[3px] border-l-red bg-panel px-[18px] py-3.5">
          <div className="flex-1">
            <div className="text-sm font-semibold text-red">Proposal failed</div>
            <div className="font-mono text-[11.5px] text-ink2">{proposeError}</div>
          </div>
          <button
            type="button"
            onClick={handleOpenProposal}
            className="cursor-pointer rounded border border-line2 bg-transparent px-[15px] py-2 text-[12.5px] font-semibold text-ink transition-colors hover:border-gold hover:text-gold-hi"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}

function ScoreRing({ score }: { score: number }) {
  return (
    <div className="relative h-[70px] w-[70px]">
      <svg
        width="70"
        height="70"
        viewBox="0 0 70 70"
        className="-rotate-90"
        aria-hidden
      >
        <circle cx="35" cy="35" r="30" fill="none" stroke="#1e1e22" strokeWidth="4" />
        <circle
          cx="35"
          cy="35"
          r="30"
          fill="none"
          stroke="var(--color-gold)"
          strokeWidth="4"
          strokeLinecap="butt"
          strokeDasharray="188"
          strokeDashoffset="15"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="font-mono text-[22px] text-ink">{score}</span>
      </div>
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] text-ink3">{label}</div>
      <div className="mt-1 font-mono text-[13px] text-ink">{value}</div>
    </div>
  );
}

function MatchCard({ match }: { match: CampaignMatch }) {
  const scoreColor = match.blocked
    ? "text-red"
    : match.score >= 80
      ? "text-green"
      : "text-ink";

  return (
    <div
      className={`flex items-center gap-3.5 rounded bg-panel px-[18px] py-[15px] ${
        match.blocked ? "opacity-60" : ""
      }`}
    >
      <div className="flex h-10 w-10 flex-none items-center justify-center rounded bg-[#19191d] text-[18px] font-bold tracking-[-0.02em] text-ink3">
        {match.brand[0]}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[14.5px] font-semibold text-ink">{match.brand}</span>
          {match.statusLabel && (
            <span className="rounded-[2px] bg-[rgba(197,107,91,0.14)] px-[7px] py-0.5 text-[9px] font-semibold tracking-[0.5px] text-red">
              {match.statusLabel}
            </span>
          )}
        </div>
        <div className="mt-0.5 text-xs text-ink2">{match.line}</div>
      </div>
      <div className="flex-none text-right">
        <div className={`font-mono text-[20px] ${scoreColor}`}>{match.score}</div>
        <div className="text-[10px] text-ink3">match</div>
      </div>
    </div>
  );
}

function MatchBreakdownPanel({
  breakdown,
  score,
}: {
  breakdown: MatchBreakdown[];
  score: number;
}) {
  return (
    <div className="self-start rounded bg-panel p-[22px]">
      <div className="text-[20px] font-bold tracking-[-0.02em] text-ink">
        Why this match?
      </div>
      <div className="mb-[18px] mt-1 text-xs text-ink2">
        Composite of Gemini semantic fit + deterministic rules.
      </div>

      <div className="flex flex-col gap-3.5">
        {breakdown.map((item) => (
          <div key={item.key}>
            <div className="mb-1.5 flex justify-between text-xs">
              <span className="text-ink">{item.key}</span>
              <span className="font-mono text-xs text-ink2">{item.value}</span>
            </div>
            <div className="h-[3px] overflow-hidden bg-[#1e1e22]">
              <div
                className="h-full bg-gold"
                style={{ width: `${item.value}%` }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 flex items-baseline justify-between border-t border-line pt-[18px]">
        <span className="text-[13px] text-ink2">Final composite</span>
        <span className="text-[34px] font-bold leading-none tracking-[-0.02em] text-gold">
          {score}
        </span>
      </div>

      <div className="mt-4 rounded bg-well p-3 text-xs leading-[1.5] text-ink2">
        Hard rules (territory, category, exclusivity) can block a campaign
        regardless of semantic score.
      </div>
    </div>
  );
}

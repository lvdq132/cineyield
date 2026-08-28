"use client";

import Link from "next/link";
import { useState } from "react";
import { Check } from "lucide-react";
import type { Proposal } from "@/lib/types";
import { Breadcrumb, SectionLabel } from "@/components/ui";
import { useAppState } from "@/context/AppStateContext";
import { getAuditTrail } from "@/data/agent-events";
import { DataSourceNotice } from "@/components/ui/DataSourceNotice";
import type { DataSource } from "@/lib/data-source";

interface DealViewProps {
  proposal: Proposal;
  initialApproved?: boolean;
  dataSource?: DataSource;
}

export function DealView({ proposal, initialApproved = false, dataSource = "live" }: DealViewProps) {
  const { approved: contextApproved, approving, approveError, approvePlacement } = useAppState();
  const [localApproved] = useState(initialApproved);
  const approved = localApproved || contextApproved;
  const audit = getAuditTrail(approved);

  async function handleApprove() {
    // approved only flips once the API call (or fixture-mode path) actually succeeds —
    // see AppStateContext.approvePlacement.
    await approvePlacement(proposal.id);
  }

  return (
    <div className="animate-cyrise">
      <Breadcrumb
        items={[
          { label: "Marketplace", href: "/marketplace" },
          { label: `Proposal · ${proposal.brandName}` },
        ]}
      />

      <div className="mb-8 grid grid-cols-1 gap-5 border-b border-line pb-7 md:grid-cols-[1fr_420px] md:items-end">
        <div><span className="font-mono text-[9px] font-bold uppercase tracking-[0.12em] text-gold">Decision room / Producer control</span><h1 className="mt-4 text-[clamp(42px,5vw,72px)] font-medium leading-[0.9] tracking-[-0.06em] text-ink">Proposal review.</h1></div>
        <p className="m-0 text-[15px] leading-[1.6] text-ink2">Review the sponsor brief, commercial terms, creative guardrails, and audit trail before approval.</p>
      </div>

      <DataSourceNotice source={dataSource} />

      {approved && (
        <div className="mb-[18px] flex animate-cyrise items-center gap-3 rounded border-l-[3px] border-l-green bg-panel px-[18px] py-3.5">
          <Check size={19} stroke="var(--color-green)" strokeWidth={2.2} aria-hidden />
          <div className="flex-1">
            <div className="text-sm font-semibold text-green">Placement approved</div>
            <div className="font-mono text-[11.5px] text-ink2">
              QUALIFIED → APPROVED · audit event recorded · analytics updated
            </div>
          </div>
          <Link
            href="/analytics"
            className="rounded border border-line2 bg-transparent px-[15px] py-2 text-[12.5px] font-semibold text-green transition-colors hover:border-gold hover:text-gold-hi"
          >
            View in Analytics →
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_336px]">
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <BriefCard
              label="BRAND BRIEF"
              title={proposal.brandName}
              subtitle={`"${proposal.campaignName}"`}
              body={proposal.brandBrief}
            />
            <BriefCard
              label="PRODUCER SCENE"
              title={proposal.sceneTitle}
              subtitle={proposal.sceneEpisode}
              body={proposal.sceneDetail}
            />
          </div>

          <div className="rounded bg-panel p-[22px]">
            <h2 className="mb-[18px] text-[20px] font-bold tracking-[-0.02em] text-ink">
              Proposed terms
            </h2>
            <div className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
              {proposal.terms.map((term) => (
                <div
                  key={term.label}
                  className="flex justify-between border-b border-line py-3"
                >
                  <span className="text-[12.5px] text-ink2">
                    {term.label}
                    {term.modelled && <sup className="ml-0.5 text-ink3">†</sup>}
                  </span>
                  <span
                    className={`text-[13px] font-semibold ${
                      term.highlight
                        ? "font-mono text-sm font-bold text-gold"
                        : "text-ink"
                    }`}
                  >
                    {term.value}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded bg-well px-[13px] py-[11px] text-[11.5px] text-ink2">
              {proposal.terms.some((t) => t.modelled) && (
                <>
                  ⓘ Fields marked <sup className="text-ink3">†</sup> are illustrative
                  deal-template terms, not confirmed by the backend for this deal.{" "}
                </>
              )}
              Estimated value is a demo planning signal, not a guaranteed
              transaction price. Producer creative approval always required.
            </div>
          </div>

          <ApprovalControls
            approved={approved}
            approving={approving}
            approveError={approveError}
            onApprove={handleApprove}
          />
        </div>

        <div className="flex flex-col gap-[18px]">
          <GuardrailsPanel guardrails={proposal.guardrails} />
          <AuditTrailPanel events={audit} />
        </div>
      </div>
    </div>
  );
}

function BriefCard({
  label,
  title,
  subtitle,
  body,
}: {
  label: string;
  title: string;
  subtitle: string;
  body: string;
}) {
  return (
    <div className="rounded bg-panel p-5">
      <div className="text-[10px] font-semibold tracking-[1.4px] text-gold">{label}</div>
      <div className="mt-2 text-[19px] font-bold tracking-[-0.02em] text-ink">
        {title}
      </div>
      <div className="mt-0.5 text-[12.5px] text-ink2">{subtitle}</div>
      <p className="mt-[13px] text-[12.5px] leading-[1.55] text-pretty text-ink">
        {body}
      </p>
    </div>
  );
}

function ApprovalControls({
  approved,
  approving,
  approveError,
  onApprove,
}: {
  approved: boolean;
  approving: boolean;
  approveError: string | null;
  onApprove: () => void;
}) {
  const disabled = approved || approving;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={disabled ? undefined : onApprove}
          disabled={disabled}
          className={`inline-flex items-center gap-2 rounded px-[22px] py-3 text-[13.5px] font-bold ${
            approved
              ? "cursor-default border border-[rgba(126,190,150,0.4)] bg-[rgba(126,190,150,0.12)] text-green"
              : approving
                ? "cursor-wait border-none bg-gold opacity-60 text-white"
                : "cursor-pointer border-none bg-gold text-white transition-[background] hover:bg-gold-hi"
          }`}
        >
          <Check size={16} strokeWidth={2.4} aria-hidden />
          {approved ? "Placement Approved" : approving ? "Approving…" : "Approve Placement"}
        </button>
        <GhostActionButton>Counter</GhostActionButton>
        <GhostActionButton>Request Changes</GhostActionButton>
        <GhostActionButton danger className="ml-auto">
          Reject
        </GhostActionButton>
      </div>

      {approveError && (
        <div className="flex animate-cyrise items-center gap-3 rounded border-l-[3px] border-l-red bg-panel px-[18px] py-3.5">
          <div className="flex-1">
            <div className="text-sm font-semibold text-red">Approval failed</div>
            <div className="font-mono text-[11.5px] text-ink2">{approveError}</div>
          </div>
          <button
            type="button"
            onClick={onApprove}
            className="cursor-pointer rounded border border-line2 bg-transparent px-[15px] py-2 text-[12.5px] font-semibold text-ink transition-colors hover:border-gold hover:text-gold-hi"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}

function GhostActionButton({
  children,
  danger,
  className = "",
}: {
  children: React.ReactNode;
  danger?: boolean;
  className?: string;
}) {
  return (
    <button
      type="button"
      className={`cursor-pointer rounded border bg-transparent px-[18px] py-3 text-[13.5px] font-semibold transition-colors hover:border-gold hover:text-gold-hi ${
        danger
          ? "border-[rgba(197,107,91,0.3)] text-red"
          : "border-line2 text-ink"
      } ${className}`}
    >
      {children}
    </button>
  );
}

function GuardrailsPanel({
  guardrails,
}: {
  guardrails: Proposal["guardrails"];
}) {
  return (
    <div className="rounded bg-panel p-5">
      <SectionLabel>GUARDRAILS</SectionLabel>
      {guardrails.length === 0 && (
        <div className="border-t border-line py-[11px] text-[11.5px] text-ink3">
          No guardrail signal available for this deal.
        </div>
      )}
      {guardrails.map((g) => (
        <div
          key={g.name}
          className="flex items-center gap-[11px] border-t border-line py-[11px]"
        >
          <span
            className="flex h-[18px] w-[18px] flex-none items-center justify-center font-mono text-[13px] font-bold"
            style={{
              color:
                g.statusColor === "green"
                  ? "var(--color-green)"
                  : "var(--color-amber)",
            }}
          >
            {g.mark}
          </span>
          <div className="flex-1">
            <div className="text-[12.5px] font-semibold text-ink">{g.name}</div>
            <div className="text-[11px] text-ink3">{g.detail}</div>
          </div>
          <span
            className="text-[10px] font-semibold tracking-[0.5px]"
            style={{
              color:
                g.statusColor === "green"
                  ? "var(--color-green)"
                  : "var(--color-amber)",
            }}
          >
            {g.status}
          </span>
        </div>
      ))}
    </div>
  );
}

function AuditTrailPanel({
  events,
}: {
  events: ReturnType<typeof getAuditTrail>;
}) {
  return (
    <div className="rounded bg-panel p-5">
      <SectionLabel>AUDIT TRAIL</SectionLabel>
      <div className="flex flex-col">
        {events.map((event, i) => (
          <div key={`${event.text}-${i}`} className="flex gap-3 pb-[15px]">
            <div className="flex flex-col items-center">
              <span
                className="mt-0.5 h-2 w-2 flex-none rounded-full"
                style={{
                  background:
                    event.dotColor === "green"
                      ? "var(--color-green)"
                      : "var(--color-gold)",
                }}
              />
              {i < events.length - 1 && (
                <span className="mt-0.5 w-px flex-1 bg-line2" />
              )}
            </div>
            <div className="-mt-0.5 flex-1">
              <div className="text-[12.5px] text-ink">{event.text}</div>
              <div className="mt-0.5 font-mono text-[10px] text-ink3">
                {event.who} · {event.time}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

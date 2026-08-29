"use client";

import Link from "next/link";
import { useState } from "react";
import { Check, MessageSquareText, X } from "lucide-react";
import type { Proposal } from "@/lib/types";
import { Breadcrumb, SectionLabel } from "@/components/ui";
import {
  useAppState,
  type DealWorkflowState,
} from "@/context/AppStateContext";
import { getAuditTrail } from "@/data/agent-events";
import { DataSourceNotice } from "@/components/ui/DataSourceNotice";
import type { DataSource } from "@/lib/data-source";
import type { DealDecisionAction } from "@/lib/api-client";
import { BrandedMediaStudio } from "@/components/deal/BrandedMediaStudio";

interface DealViewProps {
  proposal: Proposal;
  initialApproved?: boolean;
  initialWorkflowState?: string;
  dataSource?: DataSource;
}

export function DealView({
  proposal,
  initialApproved = false,
  initialWorkflowState = "PRODUCER_REVIEW",
  dataSource = "live",
}: DealViewProps) {
  const {
    approved: contextApproved,
    approving,
    approveError,
    dealWorkflowState,
    approvePlacement,
    decidePlacement,
  } = useAppState();
  const [pendingAction, setPendingAction] = useState<DealDecisionAction | null>(null);
  const [decisionNote, setDecisionNote] = useState("");
  const workflowState = (dealWorkflowState ?? initialWorkflowState) as DealWorkflowState;
  const approved = dealWorkflowState
    ? dealWorkflowState === "APPROVED"
    : workflowState === "APPROVED" || initialApproved || contextApproved;
  const audit = getAuditTrail(approved);

  async function handleApprove() {
    // approved only flips once the API call (or fixture-mode path) actually succeeds —
    // see AppStateContext.approvePlacement.
    await approvePlacement(proposal.id);
  }

  async function handleDecision() {
    if (!pendingAction) return;
    const succeeded = await decidePlacement(proposal.id, pendingAction, decisionNote.trim());
    if (succeeded) {
      setPendingAction(null);
      setDecisionNote("");
    }
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

      {!approved && workflowState !== "PRODUCER_REVIEW" && (
        <DecisionStatusBanner state={workflowState} />
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
            pendingAction={pendingAction}
            onChooseAction={setPendingAction}
            decisionNote={decisionNote}
            onDecisionNoteChange={setDecisionNote}
            onSubmitDecision={handleDecision}
            onCancelDecision={() => {
              setPendingAction(null);
              setDecisionNote("");
            }}
          />
        </div>

        <div className="flex flex-col gap-[18px]">
          <GuardrailsPanel guardrails={proposal.guardrails} />
          <AuditTrailPanel events={audit} />
        </div>
      </div>

      <BrandedMediaStudio proposalId={proposal.id} dealApproved={approved} />
    </div>
  );
}

function DecisionStatusBanner({ state }: { state: DealWorkflowState }) {
  const copy: Record<Exclude<DealWorkflowState, "PRODUCER_REVIEW" | "APPROVED">, { title: string; detail: string }> = {
    REJECTED: {
      title: "Placement rejected",
      detail: "Decision recorded · sponsor inventory released",
    },
    COUNTERED: {
      title: "Counter sent",
      detail: "Producer terms recorded · awaiting sponsor response",
    },
    CHANGES_REQUESTED: {
      title: "Changes requested",
      detail: "Creative notes recorded · proposal returned for revision",
    },
  };
  if (!(state in copy)) return null;
  const status = copy[state as keyof typeof copy];
  return (
    <div className="mb-[18px] flex animate-cyrise items-center gap-3 border-l-[3px] border-l-gold bg-panel px-[18px] py-3.5">
      <MessageSquareText size={18} stroke="var(--color-gold)" aria-hidden />
      <div>
        <div className="text-sm font-semibold text-ink">{status.title}</div>
        <div className="font-mono text-[11.5px] text-ink2">{status.detail}</div>
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
  pendingAction,
  onChooseAction,
  decisionNote,
  onDecisionNoteChange,
  onSubmitDecision,
  onCancelDecision,
}: {
  approved: boolean;
  approving: boolean;
  approveError: string | null;
  onApprove: () => void;
  pendingAction: DealDecisionAction | null;
  onChooseAction: (action: DealDecisionAction) => void;
  decisionNote: string;
  onDecisionNoteChange: (value: string) => void;
  onSubmitDecision: () => void;
  onCancelDecision: () => void;
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
        <GhostActionButton
          onClick={() => onChooseAction("counter")}
          active={pendingAction === "counter"}
          disabled={approving}
        >
          Counter
        </GhostActionButton>
        <GhostActionButton
          onClick={() => onChooseAction("request_changes")}
          active={pendingAction === "request_changes"}
          disabled={approving}
        >
          Request Changes
        </GhostActionButton>
        <GhostActionButton
          danger
          className="ml-auto"
          onClick={() => onChooseAction("reject")}
          active={pendingAction === "reject"}
          disabled={approving}
        >
          Reject
        </GhostActionButton>
      </div>

      {pendingAction && pendingAction !== "approve" && (
        <div className="animate-cyrise border border-line2 bg-panel p-4" role="group" aria-label="Producer decision details">
          <div className="mb-3 flex items-start justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-ink">
                {pendingAction === "counter"
                  ? "Send counter terms"
                  : pendingAction === "request_changes"
                    ? "Request proposal changes"
                    : "Reject this placement"}
              </div>
              <p className="mt-1 text-xs leading-5 text-ink2">
                This decision is written to the proposal workflow and producer audit trail.
              </p>
            </div>
            <button
              type="button"
              onClick={onCancelDecision}
              className="cursor-pointer text-ink3 transition-colors hover:text-ink"
              aria-label="Cancel decision"
            >
              <X size={18} aria-hidden />
            </button>
          </div>
          <label className="block">
            <span className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.08em] text-ink2">
              Producer note {pendingAction === "reject" ? "(optional)" : "(required)"}
            </span>
            <textarea
              value={decisionNote}
              onChange={(event) => onDecisionNoteChange(event.target.value)}
              rows={3}
              placeholder={
                pendingAction === "counter"
                  ? "State the revised fee, territory, or usage terms…"
                  : pendingAction === "request_changes"
                    ? "Describe the creative or legal changes required…"
                    : "Add a reason for the audit trail…"
              }
              className="w-full resize-y border border-line2 bg-well px-3 py-2.5 text-[13px] leading-5 text-ink outline-none placeholder:text-ink3 focus:border-gold"
            />
          </label>
          <div className="mt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={onCancelDecision}
              className="cursor-pointer border border-line2 px-4 py-2 text-xs font-semibold text-ink2 hover:border-ink3 hover:text-ink"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onSubmitDecision}
              disabled={approving || (pendingAction !== "reject" && !decisionNote.trim())}
              className="cursor-pointer bg-gold px-4 py-2 text-xs font-bold text-white hover:bg-gold-hi disabled:cursor-not-allowed disabled:opacity-40"
            >
              {approving ? "Recording…" : "Confirm decision"}
            </button>
          </div>
        </div>
      )}

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
  onClick,
  active,
  disabled,
}: {
  children: React.ReactNode;
  danger?: boolean;
  className?: string;
  onClick?: () => void;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-pressed={active}
      className={`cursor-pointer rounded border px-[18px] py-3 text-[13.5px] font-semibold transition-colors hover:border-gold hover:text-gold-hi disabled:cursor-wait disabled:opacity-50 ${
        active ? "border-gold bg-[rgba(241,93,59,0.08)] text-gold" : "bg-transparent"
      } ${
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

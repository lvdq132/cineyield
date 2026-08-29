"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Check,
  Film,
  Image as ImageIcon,
  LoaderCircle,
  LockKeyhole,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import {
  ApiError,
  generations,
  resolveApiUrl,
  type ApiGenerationJob,
  type GenerationWorkflowResponse,
} from "@/lib/api-client";

interface BrandedMediaStudioProps {
  proposalId: string;
  dealApproved: boolean;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return String(error);
}

export function BrandedMediaStudio({ proposalId, dealApproved }: BrandedMediaStudioProps) {
  const [workflow, setWorkflow] = useState<GenerationWorkflowResponse | null>(null);
  const [instructions, setInstructions] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadWorkflow = useCallback(async () => {
    try {
      const next = await generations.workflow(proposalId);
      setWorkflow(next);
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [proposalId]);

  useEffect(() => {
    void loadWorkflow();
  }, [loadWorkflow, dealApproved]);

  const processingVideo = workflow?.latest_video?.status === "PROCESSING";
  useEffect(() => {
    if (!processingVideo) return;
    const timer = window.setInterval(() => void loadWorkflow(), 8000);
    return () => window.clearInterval(timer);
  }, [processingVideo, loadWorkflow]);

  async function createImage() {
    setBusy("image");
    setError(null);
    try {
      await generations.createImage(proposalId, instructions);
      await loadWorkflow();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function decide(job: ApiGenerationJob, decision: "approve" | "reject") {
    setBusy(`${job.id}:${decision}`);
    setError(null);
    try {
      await generations.decide(job.id, decision);
      await loadWorkflow();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function createVideo() {
    setBusy("video");
    setError(null);
    try {
      await generations.createVideo(proposalId);
      await loadWorkflow();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  const approvedByEitherSource = dealApproved || workflow?.deal_approved === true;
  const originalFrame = resolveApiUrl(workflow?.original_frame_url);
  const originalVideo = resolveApiUrl(workflow?.original_video_url);
  const imageUrl = resolveApiUrl(workflow?.latest_image?.media_url);
  const videoUrl = resolveApiUrl(workflow?.latest_video?.media_url);

  return (
    <section className="mt-6 border border-line bg-panel" aria-labelledby="branded-media-title">
      <header className="grid gap-5 border-b border-line px-5 py-5 md:grid-cols-[1fr_auto] md:items-end md:px-6">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-gold">
            <Sparkles size={13} aria-hidden /> Google generative media
          </div>
          <h2 id="branded-media-title" className="text-[26px] font-semibold tracking-[-0.035em] text-ink">
            Branded replacement studio
          </h2>
          <p className="mt-2 max-w-[680px] text-[13px] leading-5 text-ink2">
            Approve the terms, create a scene-preserving sponsor frame with Nano Banana,
            then use that approved frame and the original segment&apos;s continuity signals to generate the final Veo shot.
          </p>
        </div>
        <div className="font-mono text-[10px] uppercase tracking-[0.08em] text-ink3">
          {workflow ? `${workflow.sponsor} · ${workflow.product}` : "Loading source context…"}
        </div>
      </header>

      {error && (
        <div className="border-b border-line bg-[rgba(241,93,59,0.06)] px-5 py-3 text-[12px] text-ink md:px-6">
          {error}
        </div>
      )}

      <div className="grid lg:grid-cols-[170px_1fr]">
        <WorkflowRail workflow={workflow} dealApproved={approvedByEitherSource} />
        <div className="min-w-0 p-5 md:p-6">
          {!approvedByEitherSource ? (
            <LockedStage
              title="Commercial approval required"
              detail="Approve the proposal above to unlock a real Nano Banana placement preview."
            />
          ) : !workflow ? (
            <LoadingStage label="Loading the uploaded scene and sponsor brief…" />
          ) : (
            <div className="space-y-8">
              <section aria-labelledby="reference-frame-title">
                <StageHeading
                  eyebrow="02 / Reference frame"
                  title="Place the sponsor without changing the scene."
                  detail="The left plate is the exact frame extracted from the upload. The right plate is a full-frame localized edit—never a crop, overlay, box, or fake mockup."
                />

                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  <MediaPlate label="Original · uploaded source">
                    {originalFrame ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={originalFrame} alt="Original extracted source frame" className="h-full w-full object-contain" />
                    ) : (
                      <EmptyPlate icon={<ImageIcon size={22} />} label="Source frame unavailable" />
                    )}
                  </MediaPlate>
                  <MediaPlate
                    label={workflow.latest_image ? `Proposal · revision ${workflow.latest_image.generation_number}` : "Proposal · not generated"}
                    status={workflow.latest_image?.decision}
                  >
                    {busy === "image" ? (
                      <LoadingStage label="Nano Banana is integrating the sponsor product…" compact />
                    ) : imageUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={imageUrl} alt="Nano Banana branded placement proposal" className="h-full w-full object-contain" />
                    ) : workflow.latest_image?.status === "FAILED" ? (
                      <EmptyPlate icon={<X size={22} />} label={workflow.latest_image.error || "Generation failed"} />
                    ) : (
                      <EmptyPlate icon={<Sparkles size={22} />} label="Generate the first branded proposal" />
                    )}
                  </MediaPlate>
                </div>

                <label className="mt-4 block">
                  <span className="mb-2 block text-[10px] font-bold uppercase tracking-[0.1em] text-ink2">
                    Optional producer direction
                  </span>
                  <textarea
                    value={instructions}
                    onChange={(event) => setInstructions(event.target.value)}
                    rows={2}
                    maxLength={1200}
                    placeholder="Example: place the headphones on the table edge, logo facing camera, keep the actor unobstructed."
                    className="w-full resize-y border border-line2 bg-well px-3.5 py-3 text-[13px] leading-5 text-ink outline-none placeholder:text-ink3 focus:border-gold"
                  />
                </label>

                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <PrimaryButton onClick={createImage} disabled={busy !== null}>
                    {busy === "image" ? <LoaderCircle className="animate-spin" size={15} /> : workflow.latest_image ? <RefreshCw size={15} /> : <Sparkles size={15} />}
                    {workflow.latest_image ? "Regenerate placement" : "Generate placement preview"}
                  </PrimaryButton>
                  {workflow.latest_image?.status === "COMPLETED" && (
                    <>
                      <DecisionButton
                        onClick={() => decide(workflow.latest_image!, "approve")}
                        disabled={busy !== null || workflow.latest_image.decision === "APPROVED"}
                        approved={workflow.latest_image.decision === "APPROVED"}
                      >
                        <Check size={14} /> {workflow.latest_image.decision === "APPROVED" ? "Reference approved" : "Approve reference"}
                      </DecisionButton>
                      <DecisionButton
                        onClick={() => decide(workflow.latest_image!, "reject")}
                        disabled={busy !== null || workflow.latest_image.decision === "REJECTED"}
                        danger
                      >
                        <X size={14} /> Reject placement
                      </DecisionButton>
                    </>
                  )}
                  <span className="ml-auto font-mono text-[10px] text-ink3">
                    {workflow.latest_image?.model ?? "gemini-3.1-flash-image"}
                  </span>
                </div>
              </section>

              <section className="border-t border-line pt-7" aria-labelledby="replacement-clip-title">
                <StageHeading
                  eyebrow="03 / Replacement clip"
                  title="Turn the approved plate into the finished shot."
                  detail="Gemini re-reads the real source segment for camera and action continuity. Veo then animates the approved branded frame under the same production constraints."
                />

                {!workflow.video_unlocked ? (
                  <div className="mt-5">
                    <LockedStage
                      title="Approve the reference frame to unlock Veo"
                      detail="Both the commercial terms and the branded reference must be approved before video generation can start."
                      compact
                    />
                  </div>
                ) : (
                  <>
                    <div className="mt-5 grid gap-3 md:grid-cols-2">
                      <MediaPlate label="Original · source segment">
                        {originalVideo ? (
                          <video className="h-full w-full object-contain" src={originalVideo} controls playsInline preload="metadata" />
                        ) : (
                          <EmptyPlate icon={<Film size={22} />} label="Source segment unavailable" />
                        )}
                      </MediaPlate>
                      <MediaPlate
                        label={workflow.latest_video ? `Branded · revision ${workflow.latest_video.generation_number}` : "Branded · not generated"}
                        status={workflow.latest_video?.decision}
                      >
                        {workflow.latest_video?.status === "PROCESSING" || busy === "video" ? (
                          <LoadingStage label="Veo is rendering the replacement clip…" compact />
                        ) : videoUrl ? (
                          <video className="h-full w-full object-contain" src={videoUrl} controls playsInline preload="metadata" />
                        ) : workflow.latest_video?.status === "FAILED" ? (
                          <EmptyPlate icon={<X size={22} />} label={workflow.latest_video.error || "Veo generation failed"} />
                        ) : (
                          <EmptyPlate icon={<Film size={22} />} label="Generate the branded replacement" />
                        )}
                      </MediaPlate>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <PrimaryButton onClick={createVideo} disabled={busy !== null || processingVideo}>
                        {processingVideo || busy === "video" ? <LoaderCircle className="animate-spin" size={15} /> : workflow.latest_video ? <RefreshCw size={15} /> : <Film size={15} />}
                        {processingVideo ? "Rendering with Veo…" : workflow.latest_video ? "Regenerate replacement clip" : "Generate Branded Replacement Clip"}
                      </PrimaryButton>
                      {workflow.latest_video?.status === "COMPLETED" && (
                        <>
                          <DecisionButton
                            onClick={() => decide(workflow.latest_video!, "approve")}
                            disabled={busy !== null || workflow.latest_video.decision === "APPROVED"}
                            approved={workflow.latest_video.decision === "APPROVED"}
                          >
                            <Check size={14} /> {workflow.latest_video.decision === "APPROVED" ? "Final clip approved" : "Approve clip"}
                          </DecisionButton>
                          <DecisionButton
                            onClick={() => decide(workflow.latest_video!, "reject")}
                            disabled={busy !== null || workflow.latest_video.decision === "REJECTED"}
                            danger
                          >
                            <X size={14} /> Reject clip
                          </DecisionButton>
                        </>
                      )}
                      <span className="ml-auto font-mono text-[10px] text-ink3">
                        {workflow.latest_video?.model ?? "veo-3.1-generate-001"}
                      </span>
                    </div>
                  </>
                )}
              </section>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function WorkflowRail({
  workflow,
  dealApproved,
}: {
  workflow: GenerationWorkflowResponse | null;
  dealApproved: boolean;
}) {
  const steps = useMemo(() => [
    { index: "01", label: "Terms approved", done: dealApproved },
    { index: "02", label: "Reference approved", done: workflow?.approved_image?.decision === "APPROVED" },
    { index: "03", label: "Clip approved", done: workflow?.latest_video?.decision === "APPROVED" },
  ], [workflow, dealApproved]);
  return (
    <aside className="border-b border-line bg-well px-5 py-5 lg:border-b-0 lg:border-r lg:px-4 lg:py-6">
      <div className="flex gap-5 lg:flex-col lg:gap-0">
        {steps.map((step, index) => (
          <div key={step.index} className="relative flex flex-1 gap-3 pb-0 lg:pb-7">
            {index < steps.length - 1 && <span className="absolute left-[11px] top-7 hidden h-[calc(100%-20px)] w-px bg-line2 lg:block" />}
            <span className={`relative z-10 flex h-[23px] w-[23px] flex-none items-center justify-center border font-mono text-[9px] ${step.done ? "border-green bg-[rgba(126,190,150,.1)] text-green" : "border-line2 bg-panel text-ink3"}`}>
              {step.done ? <Check size={11} /> : step.index}
            </span>
            <span className={`pt-0.5 text-[11px] font-semibold leading-4 ${step.done ? "text-ink" : "text-ink3"}`}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </aside>
  );
}

function StageHeading({ eyebrow, title, detail }: { eyebrow: string; title: string; detail: string }) {
  return (
    <div className="grid gap-3 md:grid-cols-[1fr_1fr] md:items-end">
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.1em] text-ink">{eyebrow}</div>
        <h3 className="mt-2 text-[22px] font-semibold leading-[1.1] tracking-[-0.03em] text-ink">{title}</h3>
      </div>
      <p className="text-[12px] leading-5 text-ink2">{detail}</p>
    </div>
  );
}

function MediaPlate({ children, label, status }: { children: React.ReactNode; label: string; status?: string }) {
  return (
    <figure className="overflow-hidden border border-line2 bg-black">
      <div className="aspect-video">{children}</div>
      <figcaption className="flex items-center justify-between border-t border-line px-3 py-2.5">
        <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-ink2">{label}</span>
        {status && status !== "PENDING" && (
          <span className={`font-mono text-[9px] ${status === "APPROVED" ? "text-green" : "text-gold"}`}>{status}</span>
        )}
      </figcaption>
    </figure>
  );
}

function EmptyPlate({ icon, label }: { icon: React.ReactNode; label: string }) {
  return <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-ink3">{icon}<span className="max-w-[260px] text-[12px] leading-5">{label}</span></div>;
}

function LockedStage({ title, detail, compact = false }: { title: string; detail: string; compact?: boolean }) {
  return (
    <div className={`flex items-start gap-4 border border-line2 bg-well ${compact ? "p-4" : "p-6"}`}>
      <LockKeyhole size={19} className="mt-0.5 flex-none text-gold" />
      <div><div className="text-[14px] font-semibold text-ink">{title}</div><p className="mt-1 text-[12px] leading-5 text-ink2">{detail}</p></div>
    </div>
  );
}

function LoadingStage({ label, compact = false }: { label: string; compact?: boolean }) {
  return <div className={`flex h-full items-center justify-center gap-3 text-ink2 ${compact ? "min-h-[180px]" : "min-h-[260px]"}`}><LoaderCircle size={18} className="animate-spin text-gold" /><span className="text-[12px]">{label}</span></div>;
}

function PrimaryButton({ children, onClick, disabled }: { children: React.ReactNode; onClick: () => void; disabled?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className="inline-flex cursor-pointer items-center gap-2 bg-gold px-4 py-2.5 text-[12px] font-bold text-white transition-colors hover:bg-gold-hi disabled:cursor-not-allowed disabled:opacity-45">{children}</button>;
}

function DecisionButton({ children, onClick, disabled, approved, danger }: { children: React.ReactNode; onClick: () => void; disabled?: boolean; approved?: boolean; danger?: boolean }) {
  return <button type="button" onClick={onClick} disabled={disabled} className={`inline-flex cursor-pointer items-center gap-2 border px-4 py-2.5 text-[12px] font-semibold transition-colors disabled:cursor-default disabled:opacity-60 ${approved ? "border-green text-green" : danger ? "border-line2 text-ink2 hover:border-gold hover:text-gold" : "border-line2 text-ink hover:border-green hover:text-green"}`}>{children}</button>;
}

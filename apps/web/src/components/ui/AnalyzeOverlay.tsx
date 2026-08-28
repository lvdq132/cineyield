"use client";

import { Check } from "lucide-react";
import { getAnalyzeStepStatus, useAppState } from "@/context/AppStateContext";
import { ANALYZE_SOURCE } from "@/data/agent-events";

interface AnalyzeOverlayProps {
  progress: number;
}

export function AnalyzeOverlay({ progress }: AnalyzeOverlayProps) {
  const { analyzeFileName } = useAppState();
  const steps = getAnalyzeStepStatus(progress);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(10,8,6,0.78)]">
      <div className="w-[min(452px,calc(100vw-40px))] border border-line2 border-t-2 border-t-gold bg-panel2 p-7">
        <div className="mb-1 flex items-center gap-3">
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-gold)"
            strokeWidth="1.8"
            className="flex-none"
            aria-hidden
          >
            <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
            <circle cx="12" cy="12" r="3.5" />
          </svg>
          <div>
            <div className="text-[20px] font-bold leading-[1.1] tracking-[-0.02em] text-ink">
              Analyzing cut
            </div>
            <div className="font-mono text-[11px] text-ink2">{analyzeFileName ?? ANALYZE_SOURCE}</div>
          </div>
        </div>

        <div className="my-5 mb-1.5 h-1 overflow-hidden bg-[#1e1e22]">
          <div
            className="h-full bg-gold transition-[width] duration-200"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="mb-[18px] text-right font-mono text-[11px] text-ink3">
          {Math.round(progress)}%
        </div>

        <div className="flex flex-col gap-3">
          {steps.map((step) => (
            <div key={step.label} className="flex items-center gap-3">
              {step.done ? (
                <span className="flex h-[18px] w-[18px] flex-none items-center justify-center rounded-full bg-gold">
                  <Check size={10} strokeWidth={3.4} className="text-white" aria-hidden />
                </span>
              ) : step.active ? (
                <span className="h-[18px] w-[18px] flex-none animate-cyspin rounded-full border-2 border-gold border-t-transparent" />
              ) : (
                <span className="h-[18px] w-[18px] flex-none rounded-full border-2 border-[#232327]" />
              )}
              <span
                className={`text-[13px] ${
                  step.done ? "text-ink" : step.active ? "text-gold" : "text-ink3"
                }`}
              >
                {step.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import {
  ANALYZE_TARGET_SCENE,
  demoAnalyzeSteps,
} from "@/data/agent-events";
import {
  ingest,
  deals,
  ApiError,
  type DealDecisionAction,
} from "@/lib/api-client";

export type DealWorkflowState =
  | "PRODUCER_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "COUNTERED"
  | "CHANGES_REQUESTED";

interface AppState {
  analyzing: boolean;
  progress: number;
  approved: boolean;
  approving: boolean;
  approveError: string | null;
  dealWorkflowState: DealWorkflowState | null;
  analyzeFileName: string | null;
  analyzeError: string | null;
}

interface AppStateContextValue extends AppState {
  startAnalyze: () => void;
  analyzeWithFile: (file: File) => void;
  approvePlacement: (dealId?: string) => Promise<void>;
  decidePlacement: (
    dealId: string,
    action: DealDecisionAction,
    note?: string,
  ) => Promise<boolean>;
  registerFileInput: (el: HTMLInputElement | null) => void;
}

const AppStateContext = createContext<AppStateContextValue | null>(null);

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export function AppStateProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AppState>({
    analyzing: false,
    progress: 0,
    approved: false,
    approving: false,
    approveError: null,
    dealWorkflowState: null,
    analyzeFileName: null,
    analyzeError: null,
  });
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  const registerFileInput = useCallback((el: HTMLInputElement | null) => {
    fileInputRef.current = el;
  }, []);

  // Fixture-mode fake animation
  const _runFakeAnalysis = useCallback(() => {
    if (state.analyzing) return;
    setState((prev) => ({ ...prev, analyzing: true, progress: 0, analyzeFileName: "HORIZONS_S2E3_rooftop.mp4", analyzeError: null }));
    let p = 0;
    timerRef.current = setInterval(() => {
      p = Math.min(100, p + 8 + Math.random() * 6);
      setState((prev) => ({ ...prev, progress: p }));
      if (p >= 100) {
        if (timerRef.current) clearInterval(timerRef.current);
        timerRef.current = null;
        timeoutRef.current = setTimeout(() => {
          setState((prev) => ({ ...prev, analyzing: false }));
          router.push(`/scene/${ANALYZE_TARGET_SCENE}`);
        }, 550);
      }
    }, 220);
  }, [state.analyzing, router]);

  const startAnalyze = useCallback(() => {
    if (state.analyzing) return;
    if (API_BASE && fileInputRef.current) {
      fileInputRef.current.click();
    } else {
      _runFakeAnalysis();
    }
  }, [state.analyzing, _runFakeAnalysis]);

  const analyzeWithFile = useCallback(async (file: File) => {
    if (state.analyzing) return;
    setState((prev) => ({
      ...prev,
      analyzing: true,
      progress: 5,
      analyzeFileName: file.name,
      analyzeError: null,
    }));

    try {
      const job = await ingest.uploadVideo(file);

      // Poll for completion, advancing progress from 10→90.
      // 404 on the status endpoint means Cloud Run routed this poll to a replica
      // that has not yet received the in-memory job — treat as transient and retry.
      let attempt = 0;
      let notFoundStreak = 0;
      const MAX_NOT_FOUND = 30; // give up after 60 s of consistent 404s
      while (true) {
        attempt++;
        let status: Awaited<ReturnType<typeof ingest.pollStatus>> | null = null;
        try {
          status = await ingest.pollStatus(job.job_id);
          notFoundStreak = 0;
        } catch (pollErr) {
          // 404 = job not yet visible on this replica; anything else = propagate.
          if (pollErr instanceof ApiError && pollErr.status === 404) {
            notFoundStreak++;
            if (notFoundStreak >= MAX_NOT_FOUND) {
              throw new Error("Analysis job not found after repeated attempts. The pipeline may have failed.");
            }
            await new Promise((r) => setTimeout(r, 2000));
            continue;
          }
          throw pollErr;
        }

        if (status.status === "completed") {
          const sceneId = status.scene_analysis?.scene_id ?? ANALYZE_TARGET_SCENE;
          setState((prev) => ({ ...prev, progress: 100 }));
          await new Promise((r) => setTimeout(r, 400));
          setState((prev) => ({ ...prev, analyzing: false }));
          router.push(`/scene/${sceneId}`);
          return;
        }

        if (status.status === "failed") {
          throw new Error(status.error ?? "Analysis failed");
        }

        // Ramp progress toward 90 asymptotically
        const progressTarget = Math.min(90, 10 + attempt * 8);
        setState((prev) => ({ ...prev, progress: progressTarget }));
        await new Promise((r) => setTimeout(r, 2000));
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setState((prev) => ({ ...prev, analyzing: false, progress: 0, analyzeError: msg }));
    }
  }, [state.analyzing, router]);

  const decidePlacement = useCallback(async (
    dealId: string,
    action: DealDecisionAction,
    note = "",
  ): Promise<boolean> => {
    setState((prev) => ({ ...prev, approving: true, approveError: null }));

    const stateByAction: Record<DealDecisionAction, DealWorkflowState> = {
      approve: "APPROVED",
      reject: "REJECTED",
      counter: "COUNTERED",
      request_changes: "CHANGES_REQUESTED",
    };

    try {
      if (API_BASE) {
        const result = await deals.decide(dealId, {
          action,
          approver: "producer",
          note,
        });
        const workflowState = (result.workflow_state ?? stateByAction[action]) as DealWorkflowState;
        setState((prev) => ({
          ...prev,
          approved: workflowState === "APPROVED",
          approving: false,
          approveError: null,
          dealWorkflowState: workflowState,
        }));
      } else {
        // Disclosed offline demo mode: preserve the same interaction semantics
        // without claiming a server-side write occurred.
        const workflowState = stateByAction[action];
        setState((prev) => ({
          ...prev,
          approved: workflowState === "APPROVED",
          approving: false,
          approveError: null,
          dealWorkflowState: workflowState,
        }));
      }
      return true;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setState((prev) => ({ ...prev, approving: false, approveError: msg }));
      return false;
    }
  }, []);

  const approvePlacement = useCallback(async (dealId?: string) => {
    if (!dealId) {
      setState((prev) => ({
        ...prev,
        approved: true,
        approving: false,
        approveError: null,
        dealWorkflowState: "APPROVED",
      }));
      return;
    }
    await decidePlacement(dealId, "approve");
  }, [decidePlacement]);

  return (
    <AppStateContext.Provider
      value={{
        ...state,
        startAnalyze,
        analyzeWithFile,
        approvePlacement,
        decidePlacement,
        registerFileInput,
      }}
    >
      {children}
    </AppStateContext.Provider>
  );
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) {
    throw new Error("useAppState must be used within AppStateProvider");
  }
  return ctx;
}

export function getAnalyzeStepStatus(progress: number) {
  return demoAnalyzeSteps.map((step, index) => {
    const done = progress >= step.threshold;
    const prevThreshold = index > 0 ? demoAnalyzeSteps[index - 1].threshold : 0;
    const active = !done && progress >= prevThreshold && progress < step.threshold;
    return { ...step, done, active };
  });
}

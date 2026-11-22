import {
  createContext,
  type ReactNode,
  type Dispatch as SetState,
  type SetStateAction,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { ApiError, type ApiResult } from "../api/client";
import { reconcileJob } from "../domain/jobs";
import { ContractError, type JsonObject, text } from "../domain/json";
import type { Comparison, Dispatch, JobInfo, JobResult } from "../domain/planning";
import { emptyDraft, executionBlock, type ScenarioDraft } from "../domain/scenario";
import { useWorkspace } from "./Workspace";

export interface Review {
  specification: JsonObject;
  optimizer: boolean;
}
export interface JobBinding {
  id: string;
  baselineId: string;
  fingerprint: string;
  specification: JsonObject | null;
  retryAfterMs: number | null;
}
export interface Receipt {
  binding: JobBinding;
  info: JobInfo;
  requestId: string;
  result: JobResult | null;
  resultRequestId: string | null;
}
interface Value {
  reference: ApiResult<Dispatch> | null;
  comparison: ApiResult<Comparison> | null;
  draft: ScenarioDraft;
  updateDraft: (draft: ScenarioDraft) => void;
  review: Review | null;
  setReview: SetState<SetStateAction<Review | null>>;
  busy: string | null;
  error: ApiError | null;
  jobs: Receipt[];
  activeJob: string | null;
  setActiveJob: SetState<SetStateAction<string | null>>;
  runReference: () => Promise<void>;
  runComparison: () => Promise<void>;
  submitJob: (scenario: boolean) => Promise<void>;
  storeInfo: (id: string, result: ApiResult<JobInfo>) => void;
  storeResult: (binding: JobBinding, result: ApiResult<JobResult>) => void;
  forgetJob: (id: string) => void;
}
const Context = createContext<Value | null>(null);
export const safeError = (error: unknown) =>
  error instanceof ApiError ? error : new ApiError("contract");
export function validateResult(binding: JobBinding, result: JobResult): void {
  if (result.id !== binding.id) throw new ContractError();
  const output = result.output;
  if (binding.specification) {
    if (
      output.kind !== "scenarios" ||
      output.comparison.baselineId !== binding.baselineId ||
      output.comparison.baselineFingerprint !== binding.fingerprint ||
      output.comparison.id !== text(binding.specification.scenario_id)
    )
      throw new ContractError();
  } else if (
    output.kind !== "scheduling" ||
    output.instanceId !== binding.baselineId ||
    output.fingerprint !== binding.fingerprint
  )
    throw new ContractError();
}
export function PlanningProvider({ children }: { children: ReactNode }) {
  const { api, dataset, capabilities, rejectSession } = useWorkspace();
  const [reference, setReference] = useState<ApiResult<Dispatch> | null>(null);
  const [comparison, setComparison] = useState<ApiResult<Comparison> | null>(null);
  const [draft, setDraft] = useState(emptyDraft);
  const [review, setReview] = useState<Review | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [jobs, setJobs] = useState<Receipt[]>([]);
  const [activeJob, setActiveJob] = useState<string | null>(null);
  const infos = useRef(new Map<string, JobInfo>());
  const lock = useRef(false),
    mounted = useRef(true),
    pending = useRef(new Set<AbortController>());
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      for (const request of pending.current) request.abort();
    };
  }, []);
  const perform = async (label: string, action: (signal: AbortSignal) => Promise<void>) => {
    if (lock.current || !api || executionBlock(dataset, capabilities)) return;
    lock.current = true;
    setBusy(label);
    setError(null);
    const controller = new AbortController();
    pending.current.add(controller);
    try {
      await action(controller.signal);
    } catch (failure) {
      if (!controller.signal.aborted && mounted.current) {
        const e = safeError(failure);
        setError(e);
        rejectSession(e);
      }
    } finally {
      pending.current.delete(controller);
      lock.current = false;
      if (mounted.current) setBusy(null);
    }
  };
  const runReference = () =>
    perform("Running reference scheduling", async (signal) => {
      if (!api || !dataset?.instance) return;
      setReference(null);
      setComparison(null);
      setReview(null);
      const response = await api.dispatch(dataset.instance, signal);
      if (
        dataset.validatedFingerprint &&
        response.data.fingerprint !== dataset.validatedFingerprint
      )
        throw new ContractError();
      if (!signal.aborted && mounted.current) setReference(response);
    });
  const runComparison = () =>
    perform("Comparing the reviewed scenario", async (signal) => {
      if (!api || !dataset?.instance || !reference || !review || review.optimizer) return;
      setComparison(null);
      const response = await api.compare(dataset.instance, review.specification, signal);
      if (!signal.aborted && mounted.current) setComparison(response);
    });
  const submitJob = (scenario: boolean) =>
    perform("Submitting a bounded job — POST is not idempotent", async (signal) => {
      if (
        !api ||
        !dataset?.instance ||
        !reference ||
        jobs.length >= 8 ||
        (scenario && !review?.optimizer)
      )
        return;
      const submittedSpec = scenario ? (review?.specification ?? null) : null;
      window.location.hash = "/jobs";
      const response = submittedSpec
        ? await api.submitScenario(dataset.instance, submittedSpec, signal)
        : await api.submitScheduling(dataset.instance, signal);
      if (signal.aborted || !mounted.current) return;
      const binding = {
        id: response.data.id,
        baselineId: reference.data.instanceId,
        fingerprint: reference.data.fingerprint,
        specification: submittedSpec,
        retryAfterMs: response.retryAfterMs,
      };
      infos.current.set(response.data.id, response.data);
      setJobs((current) => [
        ...current,
        {
          binding,
          info: response.data,
          requestId: response.requestId,
          result: null,
          resultRequestId: null,
        },
      ]);
      setActiveJob(response.data.id);
    });
  const storeInfo = useCallback((id: string, result: ApiResult<JobInfo>) => {
    // Synchronous receipt guard makes contradictory responses fail inside the
    // caller's async error boundary, before React renders a state update.
    const previous = infos.current.get(id);
    if (!previous) throw new ContractError();
    const info = reconcileJob(previous, result.data);
    infos.current.set(id, info);
    setJobs((current) =>
      current.map((receipt) =>
        receipt.info.id === id
          ? {
              ...receipt,
              info,
              requestId: result.requestId,
              result: info.status === "EXPIRED" ? null : receipt.result,
            }
          : receipt,
      ),
    );
  }, []);
  const storeResult = useCallback((binding: JobBinding, result: ApiResult<JobResult>) => {
    validateResult(binding, result.data);
    setJobs((current) =>
      current.map((receipt) =>
        receipt.info.id === binding.id && receipt.info.status === "SUCCEEDED"
          ? { ...receipt, result: result.data, resultRequestId: result.requestId }
          : receipt,
      ),
    );
  }, []);
  const updateDraft = (next: ScenarioDraft) => {
    if (lock.current) return;
    setDraft(next);
    setReview(null);
    setComparison(null);
    setError(null);
  };
  const forgetJob = (id: string) => {
    const currentInfo = infos.current.get(id);
    if (!currentInfo || ["RUNNING", "QUEUED"].includes(currentInfo.status)) return;
    infos.current.delete(id);
    setJobs((current) =>
      current.filter((r) => r.info.id !== id || ["RUNNING", "QUEUED"].includes(r.info.status)),
    );
    setActiveJob((current) => (current === id ? null : current));
  };
  return (
    <Context.Provider
      value={{
        reference,
        comparison,
        draft,
        updateDraft,
        review,
        setReview,
        busy,
        error,
        jobs,
        activeJob,
        setActiveJob,
        runReference,
        runComparison,
        submitJob,
        storeInfo,
        storeResult,
        forgetJob,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function usePlanning(): Value {
  const value = useContext(Context);
  if (!value) throw new Error("PlanningProvider is required.");
  return value;
}

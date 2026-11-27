import { useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { ComparisonView } from "../components/ComparisonView";
import { Gantt } from "../components/Gantt";
import {
  ActionStatus,
  AlgorithmComparison,
  EvaluationEvidence,
  PlanningGate,
  PlanSummary,
} from "../components/PlanningResults";
import { Badge, Empty, ErrorNotice, Notice, Panel, TableScroll } from "../components/ui";
import { trackingDelay, trackingLimits } from "../domain/jobs";
import { terminal } from "../domain/planning";
import { useI18n } from "../i18n/I18n";
import { type Receipt, safeError, usePlanning } from "../state/PlanningWorkspace";
import { useWorkspace } from "../state/Workspace";

function JobTracker({ receipt }: { receipt: Receipt }) {
  const { t, validationMessage, codeLabel, clockLabel } = useI18n();

  const { api, rejectSession } = useWorkspace();
  const { storeInfo, storeResult, forgetJob } = usePlanning();
  const [tracking, setTracking] = useState(
    !receipt.result &&
      receipt.info.status !== "CANCELLED" &&
      receipt.info.status !== "FAILED" &&
      receipt.info.status !== "EXPIRED",
  );
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [note, setNote] = useState("");
  const pollAbort = useRef<AbortController | null>(null),
    cancelAbort = useRef<AbortController | null>(null),
    cancelLock = useRef(false);
  const binding = receipt.binding;
  useEffect(
    () => () => {
      cancelAbort.current?.abort();
    },
    [],
  );
  useEffect(() => {
    if (!api || !tracking || cancelling) return;
    const controller = new AbortController();
    pollAbort.current = controller;
    const started = Date.now();
    let polls = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const pause = () => {
      setTracking(false);
      setNote(
        "Local tracking paused at its 60-request / 90-second budget. Server work may continue; resume explicitly.",
      );
    };
    const schedule = (retry: number | null) => {
      const delay = trackingDelay(started, Date.now(), polls, retry);
      if (delay === null) pause();
      else timer = setTimeout(() => void poll(), delay);
    };
    const poll = async () => {
      if (controller.signal.aborted) return;
      polls++;
      try {
        const status = await api.job(binding.id, controller.signal);
        if (controller.signal.aborted) return;
        if (status.data.kind !== (binding.specification ? "scenarios" : "scheduling"))
          throw new ApiError("contract");
        storeInfo(binding.id, status);
        setError(null);
        if (terminal(status.data.status)) {
          if (status.data.status === "SUCCEEDED" && status.data.hasResult) {
            const result = await api.result(binding.id, controller.signal);
            if (!controller.signal.aborted) storeResult(binding, result);
          }
          if (!controller.signal.aborted) {
            setTracking(false);
            setNote(
              "Tracking stopped on the server’s terminal status. SUCCEEDED means a verified report is available, not that CP-SAT won or proved optimal.",
            );
          }
        } else schedule(status.retryAfterMs);
      } catch (failure) {
        if (controller.signal.aborted) return;
        const safe = safeError(failure);
        setError(safe);
        rejectSession(safe);
        if (safe.kind === "busy") schedule(safe.retryAfterMs);
        else {
          setTracking(false);
          setNote(
            "Tracking stopped. The last receipt is shown; retry status explicitly when appropriate. No replacement result was invented.",
          );
        }
      }
    };
    const wallDeadline = setTimeout(() => {
      controller.abort();
      pause();
    }, trackingLimits.milliseconds);
    schedule(binding.retryAfterMs);
    return () => {
      clearTimeout(wallDeadline);
      controller.abort();
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [api, tracking, cancelling, binding, storeInfo, storeResult, rejectSession]);
  const cancel = async () => {
    if (!api || cancelLock.current || !receipt.info.canCancel) return;
    cancelLock.current = true;
    pollAbort.current?.abort();
    setTracking(false);
    setCancelling(true);
    setError(null);
    const controller = new AbortController();
    cancelAbort.current = controller;
    try {
      const response = await api.cancelJob(binding.id, controller.signal);
      if (controller.signal.aborted) return;
      storeInfo(binding.id, response);
      setNote(
        response.data.status === "SUCCEEDED"
          ? "Completion won the race; the server kept its successful result."
          : response.data.status === "CANCELLED"
            ? "The server confirms cancellation."
            : "Cancellation accepted; wait for the server to finish native cleanup.",
      );
      setTracking(
        response.data.status !== "CANCELLED" &&
          response.data.status !== "FAILED" &&
          response.data.status !== "EXPIRED",
      );
    } catch (failure) {
      if (!controller.signal.aborted) {
        const safe = safeError(failure);
        setError(safe);
        rejectSession(safe);
        setNote(
          "Cancellation outcome is unconfirmed. Refresh the actual status; do not assume the server stopped.",
        );
      }
    } finally {
      cancelLock.current = false;
      if (!controller.signal.aborted) setCancelling(false);
    }
  };
  const info = receipt.info;
  return (
    <Panel
      title={t("Selected job lifecycle")}
      description={t("Actual server status and phase; no percentage progress")}
      action={
        <Badge
          tone={info.status === "SUCCEEDED" ? "teal" : info.status === "FAILED" ? "red" : "amber"}
        >
          {codeLabel(info.status)}
        </Badge>
      }
    >
      <div className="job-identity">
        <label>
          {t("Copyable job ID")}
          <input
            readOnly
            value={info.id}
            aria-label={t("Job ID")}
            onFocus={(event) => event.target.select()}
          />
        </label>
        <span>
          {codeLabel(info.kind)} · {codeLabel(info.phase)}
        </span>
        <span role="status">
          {tracking
            ? t("Polling sequentially · at least {p0} s between requests", {
                p0: trackingLimits.interval / 1000,
              })
            : t("Local polling stopped")}
          {cancelling ? t(" · cancellation request pending") : ""}
        </span>
      </div>
      <dl className="provenance-grid">
        <div>
          <dt>{t("Submitted / started (server timestamps)")}</dt>
          <dd>
            {clockLabel(info.submitted)}
            <br />
            {info.started ? clockLabel(info.started) : t("Not started")}
          </dd>
        </div>
        <div>
          <dt>{t("Completed / retention deadline")}</dt>
          <dd>
            {info.completed ? clockLabel(info.completed) : t("Not terminal")}
            <br />
            {info.expires ? clockLabel(info.expires) : t("Not reported")}
          </dd>
        </div>
        <div>
          <dt>{t("Cancellation / retained result")}</dt>
          <dd>
            {info.cancellationRequested ? t("Stop requested") : t("No stop requested")} ·{" "}
            {info.hasResult
              ? t("Server reports result available")
              : t("No server result available")}
          </dd>
        </div>
        <div>
          <dt>{t("Failure category")}</dt>
          <dd>{info.errorCode ? codeLabel(info.errorCode) : t("None reported")}</dd>
        </div>
        <div className="full-width">
          <dt>{t("Latest metadata request ID")}</dt>
          <dd>
            <code>{receipt.requestId}</code>
          </dd>
        </div>
      </dl>
      <div className="workflow-actions">
        <button
          type="button"
          className="button"
          disabled={!api || tracking || cancelling}
          onClick={() => {
            setNote("");
            setError(null);
            setTracking(true);
          }}
        >
          {t("Resume / refresh status")}
        </button>
        <button
          type="button"
          className="button"
          disabled={!tracking || cancelling}
          onClick={() => {
            pollAbort.current?.abort();
            setTracking(false);
            setNote("Only local polling paused; the server job was not cancelled.");
          }}
        >
          {t("Pause local tracking")}
        </button>
        <button
          type="button"
          className="button button-danger"
          disabled={!api || !info.canCancel || cancelling}
          onClick={() => void cancel()}
        >
          {cancelling ? t("Requesting cancellation…") : t("Cancel server job")}
        </button>
        {terminal(info.status) && (
          <button type="button" className="text-link" onClick={() => forgetJob(info.id)}>
            {t("Forget terminal local receipt")}
          </button>
        )}
      </div>
      {note && (
        <p className="tracking-note" role="status">
          {validationMessage(note)}
        </p>
      )}
      {error && (
        <div className="panel-body">
          <ErrorNotice error={error} />
        </div>
      )}
    </Panel>
  );
}
export function Jobs() {
  const { t, codeLabel } = useI18n();

  const { dataset } = useWorkspace();
  const { jobs, activeJob, setActiveJob } = usePlanning();
  const selected = jobs.find((job) => job.info.id === activeJob);
  const output = selected?.result?.output;
  return (
    <div className="page-stack">
      <PlanningGate />
      <Notice>
        {t(
          "Volatile local jobs: one active, two waiting, at most 32 server records. This workspace retains at most eight receipts in this dataset/session. Server results expire after 300 seconds; restart loses records. Copy job IDs. Leaving this page pauses polling; changing dataset/session clears local tracking, not server work. There is no job-list or restart recovery endpoint.",
        )}
      </Notice>
      <ActionStatus />
      <Panel
        title={t("Session job receipts")}
        description={t("{p0} / 8 local receipts · IDs and results are kept only in memory", {
          p0: jobs.length,
        })}
        action={
          <a className="text-link" href="/#/scheduling">
            {t("Open scheduling →")}
          </a>
        }
      >
        <TableScroll label={t("Local job receipts")}>
          <table>
            <thead>
              <tr>
                <th scope="col">{t("Job ID")}</th>
                <th scope="col">{t("Type")}</th>
                <th scope="col">{t("Server status / phase")}</th>
                <th scope="col">{t("Inspect")}</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((receipt) => (
                <tr key={receipt.info.id}>
                  <th scope="row">
                    <code>{receipt.info.id}</code>
                  </th>
                  <td>{codeLabel(receipt.info.kind)}</td>
                  <td>
                    <Badge tone={receipt.info.status === "SUCCEEDED" ? "teal" : "neutral"}>
                      {codeLabel(receipt.info.status)}
                    </Badge>
                    <span className="cell-secondary">{codeLabel(receipt.info.phase)}</span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="text-link"
                      onClick={() => setActiveJob(receipt.info.id)}
                      aria-label={t("Inspect job {p0}", { p0: receipt.info.id })}
                    >
                      {t("Inspect")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableScroll>
        {jobs.length === 0 && (
          <Empty title={t("No submitted jobs in this context")}>
            {t(
              "Run reference scheduling, then submit a bounded scheduling or reviewed what-if comparison job. A lost POST reply may leave work without a local receipt; POST is never retried automatically.",
            )}
          </Empty>
        )}
      </Panel>
      {selected && <JobTracker key={selected.info.id} receipt={selected} />}
      {selected?.result && dataset && (
        <>
          <div className="report-receipt">
            <Badge tone="teal">{t("Verified job result")}</Badge>
            <span>
              {t("Result request ID:")} <code>{selected.resultRequestId}</code>
            </span>
            <span>
              {t("Measured whole-child wall seconds: {p0}", {
                p0: selected.result.wallSeconds ?? t("Not reported"),
              })}
            </span>
          </div>
          {output?.kind === "scheduling" ? (
            <>
              <PlanSummary metrics={output.evaluation.selected.metrics} />
              <EvaluationEvidence evaluation={output.evaluation} />
              <Gantt
                title={t("Selected optimizer-job Gantt")}
                plan={output.evaluation.selected}
                horizon={output.horizon}
                planning={dataset.planning}
              />
              <details className="panel advanced-comparisons">
                <summary>{t("All metrics & same-instance algorithm comparison")}</summary>
                <AlgorithmComparison evaluation={output.evaluation} />
              </details>
            </>
          ) : output?.kind === "scenarios" ? (
            <ComparisonView comparison={output.comparison} planning={dataset.planning} />
          ) : null}
        </>
      )}
    </div>
  );
}

import { stringify } from "lossless-json";
import { type FormEvent, useState } from "react";
import { ComparisonView } from "../components/ComparisonView";
import { ActionStatus, PlanningGate } from "../components/PlanningResults";
import { Badge, JsonBlock, Notice, Panel } from "../components/ui";
import { encodeExact } from "../domain/json";
import type { Planning } from "../domain/models";
import {
  appendChange,
  draftAssignments,
  EditorError,
  executionBlock,
  makeChange,
  type Operation,
  operations,
  specification,
} from "../domain/scenario";
import { useI18n } from "../i18n/I18n";
import { usePlanning } from "../state/PlanningWorkspace";
import { useWorkspace } from "../state/Workspace";

function defaults(planning: Planning) {
  const line = planning.lines[0],
    profile = planning.profiles.find((p) => p.lineId === line?.id),
    stop = planning.downtime[0];
  return {
    line: line?.id ?? "",
    profile: profile?.id ?? "",
    value: line?.workers ?? "0",
    shift:
      planning.shifts.find(
        (s) => !planning.assignments.some((a) => a.shiftId === s.id && a.lineId === line?.id),
      )?.id ??
      planning.shifts[0]?.id ??
      "",
    assignment: planning.assignments[0]?.id ?? "",
    downtime: stop?.id ?? "",
    id: "PLANNER-ADDED",
    start: stop?.start ?? planning.shifts[0]?.start ?? "",
    end: stop?.end ?? planning.shifts[0]?.end ?? "",
    reason: "Explicit hypothetical downtime",
  };
}
export function Scenarios() {
  const { t, validationMessage, label: textLabel, codeLabel, formValidation } = useI18n();

  const { dataset, api, capabilities, status } = useWorkspace();
  const {
    draft,
    updateDraft,
    reference,
    review,
    setReview,
    comparison,
    busy,
    jobs,
    runComparison,
    submitJob,
  } = usePlanning();
  const [operation, setOperation] = useState<Operation>("set_workers");
  const [values, setValues] = useState(() =>
    dataset
      ? defaults(dataset.planning)
      : {
          line: "",
          profile: "",
          value: "",
          shift: "",
          assignment: "",
          downtime: "",
          id: "",
          start: "",
          end: "",
          reason: "",
        },
  );
  const [formError, setFormError] = useState<string | null>(null);
  const optimizer = draft.optimizer;
  const planning = dataset?.planning;
  const update = (key: keyof typeof values, value: string) =>
    setValues((current) => ({ ...current, [key]: value }));
  const field = (key: keyof typeof values, label: string) => (
    <label>
      {textLabel(String(label))}
      <input
        type="text"
        value={values[key]}
        maxLength={key === "reason" ? 4096 : 128}
        onChange={(event) => update(key, event.target.value)}
        required
        spellCheck={false}
      />
    </label>
  );
  const select = (
    key: keyof typeof values,
    label: string,
    choices: { value: string; label: string }[],
  ) => (
    <label>
      {textLabel(String(label))}
      <select
        value={values[key]}
        required
        onChange={(event) => {
          const value = event.target.value;
          update(key, value);
          if (key === "line") {
            const p = planning?.profiles.find((p) => p.lineId === value);
            update("profile", p?.id ?? "");
            if (operation === "set_workers")
              update("value", planning?.lines.find((l) => l.id === value)?.workers ?? "0");
          }
          if (key === "profile" && operation === "set_efficiency")
            update("value", planning?.profiles.find((p) => p.id === value)?.efficiency ?? "0");
          if (key === "downtime" && operation === "replace_downtime") {
            const stop = planning?.downtime.find((s) => s.id === value);
            if (stop)
              setValues((current) => ({
                ...current,
                downtime: value,
                assignment: stop.reference,
                start: stop.start,
                end: stop.end,
                reason: stop.reason,
              }));
          }
        }}
      >
        {choices.length === 0 && <option value="">{t("No declared choices")}</option>}
        {choices.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {key === "value" && operation === "set_availability"
              ? codeLabel(choice.value)
              : choice.label}
          </option>
        ))}
      </select>
    </label>
  );
  const options = (ids: string[]) => ids.map((id) => ({ value: id, label: id }));
  const append = (event: FormEvent) => {
    event.preventDefault();
    if (!planning) return;
    try {
      const change = makeChange(operation, values, planning, draft.changes);
      updateDraft({ ...draft, changes: appendChange(draft.changes, change) });
      setFormError(null);
    } catch (e) {
      setFormError(
        e instanceof EditorError
          ? e.message
          : "The change does not match the supported input contract.",
      );
    }
  };
  const prepare = () => {
    if (!dataset || !reference) return;
    try {
      setReview({
        specification: specification(dataset, reference.data, draft, optimizer),
        optimizer,
      });
      setFormError(null);
    } catch (e) {
      setFormError(
        e instanceof EditorError
          ? e.message
          : "Review requires a valid exact scenario specification.",
      );
    }
  };
  const disabled =
    !api || !!executionBlock(dataset, capabilities) || !!busy || status === "loading";
  return (
    <div className="page-stack">
      <PlanningGate />
      <Notice>
        {t(
          "Changes are hypothetical capacity assumptions. The original baseline stays immutable. Use existing lines, profiles, capabilities and declared shifts only. Python validates the complete atomic transaction; no dangling-reference cleanup is inferred.",
        )}
      </Notice>
      {!reference && (
        <Notice>
          {t("Run reference scheduling first to obtain this baseline’s verified fingerprint.")}{" "}
          <a className="text-link" href="/#/scheduling">
            {t("Open scheduling →")}
          </a>
        </Notice>
      )}
      {planning && (
        <>
          <Panel
            title={t("1 · Build ordered changes")}
            description={t("Only the eight existing change operations are supported")}
            action={<Badge>{t("Immutable baseline")}</Badge>}
          >
            <form {...formValidation} className="scenario-form" onSubmit={append}>
              <fieldset disabled={!!busy}>
                <legend className="sr-only">{t("Supported capacity change")}</legend>
                <label>
                  {t("Change operation")}
                  <select
                    value={operation}
                    onChange={(event) => {
                      const next = event.target.value as Operation;
                      setOperation(next);
                      const v = defaults(planning);
                      if (next === "set_efficiency")
                        v.value = planning.profiles[0]?.efficiency ?? "0";
                      if (next === "set_availability")
                        v.value = planning.lines[0]?.availability ?? "available";
                      setValues(v);
                      setFormError(null);
                    }}
                  >
                    {operations.map((op) => (
                      <option key={op} value={op}>
                        {codeLabel(op)}
                      </option>
                    ))}
                  </select>
                </label>
                {(operation === "set_workers" ||
                  operation === "set_availability" ||
                  operation === "add_assignment") &&
                  select(
                    "line",
                    "Existing production line",
                    options(planning.lines.map((l) => l.id)),
                  )}
                {(operation === "set_efficiency" || operation === "add_assignment") &&
                  select(
                    "profile",
                    "Existing capacity profile",
                    options(
                      planning.profiles
                        .filter((p) => operation !== "add_assignment" || p.lineId === values.line)
                        .map((p) => p.id),
                    ),
                  )}
                {(operation === "set_workers" || operation === "set_efficiency") &&
                  field(
                    "value",
                    operation === "set_workers"
                      ? "Worker count (exact integer)"
                      : "Assumed efficiency (exact fraction 0–1)",
                  )}
                {operation === "set_availability" &&
                  select(
                    "value",
                    "Declared line availability",
                    options(["available", "unavailable"]),
                  )}
                {operation === "add_assignment" && (
                  <>
                    {field("id", "New assignment ID")}
                    {select(
                      "shift",
                      "Existing shift definition",
                      options(planning.shifts.map((s) => s.id)),
                    )}
                  </>
                )}
                {operation === "remove_assignment" &&
                  select(
                    "assignment",
                    "Existing assignment to remove",
                    options(planning.assignments.map((a) => a.id)),
                  )}
                {(operation === "remove_downtime" || operation === "replace_downtime") &&
                  select(
                    "downtime",
                    "Existing downtime ID",
                    options(planning.downtime.map((s) => s.id)),
                  )}
                {(operation === "add_downtime" || operation === "replace_downtime") && (
                  <>
                    {operation === "add_downtime" && field("id", "New downtime ID")}
                    {select(
                      "assignment",
                      "Declared / explicitly added assignment",
                      options(draftAssignments(planning, draft.changes).map((a) => a.id)),
                    )}
                    {field("start", "Start timestamp (explicit offset)")}
                    {field("end", "End timestamp (explicit offset)")}
                    {field("reason", "Hypothetical downtime reason")}
                  </>
                )}
                <div className="form-submit">
                  <button className="button" type="submit" disabled={draft.changes.length >= 64}>
                    {t("Add change to review")}
                  </button>
                  <span>{t("Ordered list · maximum 64 edits per HTTP request")}</span>
                </div>
              </fieldset>
            </form>
            <ol className="change-list">
              {draft.changes.map((change, index) => (
                <li key={encodeExact(change)}>
                  <div>
                    <strong>{codeLabel(change.operation)}</strong>
                    <code>{encodeExact(change)}</code>
                  </div>
                  <div className="change-actions">
                    <button
                      className="button button-small"
                      type="button"
                      disabled={!!busy || index === 0}
                      aria-label={t("Move change {p0} up", { p0: index + 1 })}
                      onClick={() => {
                        const changes = [...draft.changes];
                        const previous = changes[index - 1];
                        if (previous) {
                          changes[index - 1] = change;
                          changes[index] = previous;
                          updateDraft({ ...draft, changes });
                        }
                      }}
                    >
                      ↑
                    </button>
                    <button
                      className="text-link"
                      type="button"
                      disabled={!!busy}
                      aria-label={t("Remove change {p0}", { p0: index + 1 })}
                      onClick={() =>
                        updateDraft({
                          ...draft,
                          changes: draft.changes.filter((_, i) => i !== index),
                        })
                      }
                    >
                      {t("Remove")}
                    </button>
                  </div>
                </li>
              ))}
            </ol>
            {draft.changes.length === 0 && (
              <p className="table-footnote">
                {t("No changes added. An explicit empty/no-op scenario is valid.")}
              </p>
            )}
          </Panel>
          <Panel
            title={t("2 · Declare provenance & execution")}
            description={t("All fields are included in the strict versioned scenario request")}
          >
            <fieldset className="scenario-metadata" disabled={!!busy}>
              <legend className="sr-only">{t("Scenario provenance")}</legend>
              <label>
                {t("Scenario ID")}
                <input
                  value={draft.id}
                  onChange={(event) => updateDraft({ ...draft, id: event.target.value })}
                  maxLength={128}
                />
              </label>
              <label>
                {t("Scenario label")}
                <input
                  value={draft.label}
                  onChange={(event) => updateDraft({ ...draft, label: event.target.value })}
                  maxLength={256}
                />
              </label>
              <label>
                {t("Synthetic source ID")}
                <input
                  value={draft.sourceId}
                  onChange={(event) => updateDraft({ ...draft, sourceId: event.target.value })}
                  maxLength={256}
                />
              </label>
              <label className="full-width">
                {t("Assumption (single canonical entry)")}
                <textarea
                  value={draft.assumptions}
                  onChange={(event) => updateDraft({ ...draft, assumptions: event.target.value })}
                  maxLength={4096}
                  rows={3}
                />
              </label>
              <label className="checkbox-field full-width">
                <input
                  type="checkbox"
                  checked={optimizer}
                  onChange={(event) => {
                    updateDraft({ ...draft, optimizer: event.target.checked });
                  }}
                />
                {t("Request bounded CP-SAT comparison job")}
              </label>
              {optimizer && (
                <>
                  <label>
                    {t("Wall seconds per phase (0–1)")}
                    <input
                      value={draft.wall}
                      onChange={(event) => updateDraft({ ...draft, wall: event.target.value })}
                      inputMode="decimal"
                    />
                  </label>
                  <label>
                    {t("Deterministic units per phase (0–1)")}
                    <input
                      value={draft.deterministic}
                      onChange={(event) =>
                        updateDraft({ ...draft, deterministic: event.target.value })
                      }
                      inputMode="decimal"
                    />
                  </label>
                  <p className="field-help full-width">
                    {t(
                      "Explicit seed 42, worker 1, benchmark mode. Zero is an intentional no-search diagnostic and can produce UNKNOWN with verified greedy fallback. Budgets are never silently clamped.",
                    )}
                  </p>
                </>
              )}
            </fieldset>
            <div className="workflow-actions">
              <button
                type="button"
                className="button button-primary"
                disabled={!!busy || !reference || !!executionBlock(dataset, capabilities)}
                onClick={prepare}
              >
                {t("Review exact specification")}
              </button>
            </div>
          </Panel>
        </>
      )}
      {formError && (
        <div className="notice notice-error" role="alert">
          {validationMessage(formError)}
        </div>
      )}
      {review && (
        <Panel
          title={t("3 · Review before execution")}
          description={t("Exact numeric tokens · {p0}", {
            p0: review.optimizer ? t("bounded CP-SAT job") : t("synchronous greedy comparison"),
          })}
          action={<Badge tone="amber">{t("SYNTHETIC")}</Badge>}
        >
          <div className="review-json">
            <JsonBlock label={t("Exact scenario specification")}>
              {stringify(review.specification, null, 2) ?? ""}
            </JsonBlock>
          </div>
          <div className="workflow-actions">
            <button
              type="button"
              className="button button-primary"
              disabled={disabled || (review.optimizer && jobs.length >= 8)}
              onClick={() => void (review.optimizer ? submitJob(true) : runComparison())}
            >
              {review.optimizer
                ? t("Submit reviewed CP-SAT comparison job")
                : t("Run reviewed greedy comparison")}
            </button>
          </div>
          <p className="table-footnote">
            {t(
              "The backend validates this exact request atomically. Rejected requests are never retried with altered assumptions. A lost POST response may leave an admitted job; do not resubmit automatically.",
            )}
          </p>
        </Panel>
      )}
      <ActionStatus />
      {comparison && planning && (
        <>
          <div className="report-receipt">
            <Badge tone="teal">{t("Actual API comparison")}</Badge>
            <span>
              {t("Request ID:")} <code>{comparison.requestId}</code>
            </span>
          </div>
          <ComparisonView comparison={comparison.data} planning={planning} />
        </>
      )}
    </div>
  );
}

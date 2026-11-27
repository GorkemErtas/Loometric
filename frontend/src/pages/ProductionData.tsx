import { type FormEvent, useEffect, useRef, useState } from "react";
import { EntitySection, WorkingDates } from "../components/ProductionForms";
import { Badge, JsonBlock, Notice, Panel } from "../components/ui";
import { encodeExact, object, parseExact, text } from "../domain/json";
import {
  calendarOf,
  cloneInput,
  exportInput,
  inspectInput,
  newInput,
  planningOf,
  readInputFile,
  rows,
  WorkspaceInputError,
} from "../domain/production";
import { useI18n } from "../i18n/I18n";
import { useProduction } from "../state/ProductionWorkspace";
import { useWorkspace } from "../state/Workspace";

const steps = [
  "Planning assumptions",
  "Product styles",
  "Production orders",
  "Lines & capabilities",
  "Capacity profiles",
  "Shifts & breaks",
  "Production calendar",
  "Review & validate",
];
function Basics() {
  const { t, validationMessage, formValidation } = useI18n();

  const { draft, replace, setEditing, invalidate } = useProduction();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const planning = planningOf(draft),
    horizon = object(draft.horizon);
  const save = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const values = new FormData(event.currentTarget),
        next = cloneInput(draft);
      next.horizon = { start: String(values.get("start")), end: String(values.get("end")) };
      next.calendar_utc_offset_minutes = parseExact(String(values.get("offset")), 128);
      planningOf(next).assumptions = String(values.get("assumptions")).split(/\r?\n/);
      const errors = inspectInput(next).filter((e) =>
        /horizon|calendar_utc_offset|assumptions/.test(e.path),
      );
      if (errors.length)
        throw new WorkspaceInputError(errors[0]?.message ?? "Invalid planning assumptions.");
      replace(next);
      setEditing(false);
      setError(null);
      setSaved(true);
    } catch (e) {
      setError(
        e instanceof WorkspaceInputError
          ? e.message
          : "Enter exact integer offset minutes and complete explicit assumptions.",
      );
    }
  };
  return (
    <Panel
      title={t("Planning assumptions")}
      description={t(
        "Set the horizon and fixed calendar offset before creating your resources. These are hypothetical production inputs.",
      )}
    >
      <form
        {...formValidation}
        className="form-stack production-form"
        onSubmit={save}
        onChange={() => {
          invalidate();
          setEditing(true);
          setSaved(false);
        }}
      >
        <div className="production-field-grid">
          <label>
            {t("Horizon start (with offset)")}
            <input
              name="start"
              aria-label={t("Horizon start (with offset)")}
              type="text"
              required
              defaultValue={text(horizon.start)}
              placeholder="2030-01-07T08:00:00+03:00"
              maxLength={128}
            />
            <small>
              {t("Include seconds and an explicit offset. All boundaries align to whole minutes.")}
            </small>
          </label>
          <label>
            {t("Horizon end (with offset)")}
            <input
              name="end"
              type="text"
              required
              defaultValue={text(horizon.end)}
              placeholder="2030-01-07T16:00:00+03:00"
              maxLength={128}
            />
          </label>
          <label>
            {t("Fixed calendar UTC offset (minutes)")}
            <input
              name="offset"
              aria-label={t("Fixed calendar UTC offset (minutes)")}
              type="text"
              inputMode="numeric"
              required
              defaultValue={
                typeof draft.calendar_utc_offset_minutes === "string"
                  ? draft.calendar_utc_offset_minutes
                  : encodeExact(draft.calendar_utc_offset_minutes)
              }
              maxLength={5}
            />
            <small>
              {t(
                "For example, enter 180 for +03:00, 0 for UTC, or -300 for -05:00. Shift starts must use this offset; no daylight-saving rules are inferred.",
              )}
            </small>
          </label>
        </div>
        <label>
          {t("Synthetic planning assumptions (one per line)")}
          <textarea
            name="assumptions"
            aria-label={t("Synthetic planning assumptions (one per line)")}
            rows={4}
            required
            defaultValue={(planning.assumptions as string[]).join("\n")}
            maxLength={32768}
          />
          <small>
            {t(
              "Describe hypothetical standards, dedicated crews and efficiency. Only synthetic inputs belong here. Empty lines are errors.",
            )}
          </small>
        </label>
        <Notice>
          {t(
            "The frozen policy uses full batches and nonpreemptive stages on one qualified line, with release dates and ordered precedence. Materials, setups, shared crews, initial WIP and ML capacity are unsupported.",
          )}
        </Notice>
        {error && (
          <p role="alert" className="error-notice">
            {validationMessage(error)}
          </p>
        )}
        {saved && (
          <p role="status">{t("Planning assumptions saved. Continue with product styles.")}</p>
        )}
        <div className="panel-actions">
          <button type="submit" className="button button-primary">
            {t("Save planning assumptions")}
          </button>
          <button
            type="reset"
            className="button"
            onClick={() => {
              setEditing(false);
              setError(null);
              setSaved(false);
            }}
          >
            {t("Discard unsaved changes")}
          </button>
        </div>
      </form>
    </Panel>
  );
}
export function ProductionData() {
  const { t, validationMessage, locale, label: textLabel } = useI18n();

  const { draft, replace, step, setStep, editing, receipt, busy, message, validate, activate } =
    useProduction();
  const { api, capabilities, dataset, catalog, sessionId } = useWorkspace();
  const [fileError, setFileError] = useState<string | null>(null);
  const [template, setTemplate] = useState("");
  const [replacement, setReplacement] = useState<"new" | "copy" | null>(null);
  const fileGeneration = useRef(0);
  const importOwner = useRef({ draft, sessionId, key: dataset?.key });
  importOwner.current = { draft, sessionId, key: dataset?.key };
  const { setEditing } = useProduction();
  useEffect(
    () => () => {
      fileGeneration.current++;
      setEditing(false);
    },
    [setEditing],
  );
  const issues = inspectInput(draft, capabilities),
    planning = planningOf(draft),
    calendar = calendarOf(draft);
  const importFile = async (file: File) => {
    const owner = importOwner.current;
    const stamp = ++fileGeneration.current;
    setFileError(null);
    try {
      const next = await readInputFile(file, capabilities);
      if (
        stamp !== fileGeneration.current ||
        owner.draft !== importOwner.current.draft ||
        owner.sessionId !== importOwner.current.sessionId ||
        owner.key !== importOwner.current.key
      )
        return;
      replace(next);
      setStep(7);
      setReplacement(null);
    } catch (e) {
      if (stamp === fileGeneration.current)
        setFileError(
          e instanceof WorkspaceInputError ? e.message : "Unable to read scheduling JSON.",
        );
    }
  };
  const download = () => {
    try {
      const content = exportInput(draft, capabilities),
        url = URL.createObjectURL(new Blob([content], { type: "application/json;charset=utf-8" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = "loometric-synthetic-instance.json";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 0);
      setFileError(null);
    } catch (e) {
      setFileError(e instanceof WorkspaceInputError ? e.message : "Unable to export this input.");
    }
  };
  return (
    <div className="page-stack production-workspace">
      <Panel
        title={t("Your synthetic production input")}
        description={t(
          "Build a scheduling instance from forms, or edit a copy of an existing template. Work stays in this tab until you explicitly validate or activate it.",
        )}
        action={<Badge tone="amber">{t("SYNTHETIC ONLY")}</Badge>}
      >
        <p>
          {t(
            "Keep an exported JSON copy before reloading. Replacing the draft discards its edits and validation. Activating a copy replaces the current user input and clears earlier results and local job IDs; server jobs may continue.",
          )}
        </p>
        <div className="production-template-controls">
          <label>
            {t("Reusable input template")}
            <select
              value={template}
              disabled={editing || busy}
              onChange={(event) => {
                setTemplate(event.target.value);
                setReplacement(null);
              }}
            >
              <option value="">{t("Choose an executable input")}</option>
              {catalog
                .filter((d) => d.instance)
                .map((d) => (
                  <option value={d.key} key={d.key}>
                    {textLabel(d.name)}
                  </option>
                ))}
            </select>
          </label>
          <button
            type="button"
            className="button"
            disabled={!template || editing || busy}
            onClick={() => setReplacement("copy")}
          >
            {t("Edit a template copy")}
          </button>
          <button
            type="button"
            className="button"
            disabled={editing || busy}
            onClick={() => setReplacement("new")}
          >
            {t("Start an empty input")}
          </button>
        </div>
        {replacement && (
          <div className="notice">
            <p>
              {t(
                "Replace the current draft and discard its edits? Original template files and the active dataset are preserved.",
              )}
            </p>
            <div className="panel-actions">
              <button
                type="button"
                className="button"
                onClick={() => {
                  fileGeneration.current++;
                  const source = catalog.find((d) => d.key === template)?.instance;
                  if (replacement === "new") replace(newInput());
                  else if (source) replace(source);
                  setStep(0);
                  setReplacement(null);
                }}
              >
                {t("Replace draft")}
              </button>
              <button type="button" className="button" onClick={() => setReplacement(null)}>
                {t("Keep current draft")}
              </button>
            </div>
          </div>
        )}
        <div className="production-transfer-controls">
          <label>
            {t("Import local scheduling JSON (replaces draft)")}
            <input
              type="file"
              accept=".json,application/json"
              disabled={editing || busy}
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                if (file) void importFile(file);
              }}
            />
            <small>
              {t(
                "At most 256 KiB; strict UTF-8, schema 1, depth 24. Import performs preliminary checks only and sends no network request. Inspection CSV is unsupported.",
              )}
            </small>
          </label>
          <button
            type="button"
            className="button"
            disabled={issues.length > 0 || editing || busy}
            onClick={download}
          >
            {t("Export scheduling JSON")}
          </button>
        </div>
        {fileError && (
          <p role="alert" className="error-notice">
            {validationMessage(fileError)}
          </p>
        )}
      </Panel>
      <nav aria-label={t("Production data steps")} className="production-steps">
        {steps.map((name, i) => (
          <button
            type="button"
            key={textLabel(name)}
            aria-current={step === i ? "step" : undefined}
            disabled={editing || busy}
            onClick={() => setStep(i)}
          >
            <span>{i + 1}</span>
            {textLabel(name)}
          </button>
        ))}
      </nav>
      <p className="field-help" role="status">
        {t("Step {p0} of {p1}: {p2}. {p3}", {
          p0: step + 1,
          p1: steps.length,
          p2: textLabel(steps[step] ?? ""),
          p3: editing
            ? t("Save or cancel the open form before moving to another step.")
            : t("{p0} preliminary issue{p1}. Frontend checks are not authoritative.", {
                p0: issues.length,
                p1: locale === "en-US" && issues.length !== 1 ? "s" : "",
              }),
        })}
      </p>
      <div key={step}>
        {step === 0 && <Basics key={encodeExact(draft.instance_id)} />}
        {step === 1 && (
          <EntitySection
            kind="styles"
            title={t("Product styles")}
            description={t(
              "Define supported stages and exact standard worker-minutes per piece. Style definitions can be reused by many orders.",
            )}
          />
        )}
        {step === 2 && (
          <EntitySection
            kind="orders"
            title={t("Production orders")}
            description={t(
              "Declare integer piece quantities, priority (1 highest), release/due dates and an ordered route through supported style stages.",
            )}
          />
        )}
        {step === 3 && (
          <div className="page-stack">
            <EntitySection
              kind="lines"
              title={t("Production lines")}
              description={t(
                "Each line has one stage and a dedicated crew. Availability and crew size are explicit assumptions.",
              )}
            />
            <EntitySection
              kind="capabilities"
              title={t("Line capabilities")}
              description={t(
                "Explicit line/style/stage qualification is required. Matching stage names alone does not create a capability.",
              )}
            />
          </div>
        )}
        {step === 4 && (
          <EntitySection
            kind="capacity_profiles"
            title={t("Capacity profiles")}
            description={t(
              "Assign an effective date, synthetic source and exact efficiency fraction to a line. Profile selection is explicit in the calendar; no latest-profile inference occurs.",
            )}
          />
        )}
        {step === 5 && (
          <EntitySection
            kind="shifts"
            title={t("Shifts")}
            description={t(
              "Declare dated start/end times and positioned breaks. Reuse shift definitions across distinct lines. Python checks all interval interactions.",
            )}
          />
        )}
        {step === 6 && (
          <div className="page-stack">
            <WorkingDates />
            <EntitySection
              kind="assignments"
              title={t("Shift assignments")}
              description={t(
                "Choose a line, declared shift and a profile belonging to that line. The profile must be effective on the explicit shift start working date.",
              )}
            />
            <EntitySection
              kind="planned_downtime"
              title={t("Planned downtime")}
              description={t(
                "Stops must remain inside their assigned shift. Overlapping exclusion reasons are handled by Python's existing interval union.",
              )}
            />
            <EntitySection
              kind="unavailable_periods"
              title={t("Unavailable periods")}
              description={t(
                "Line-wide unavailable intervals may span shifts. Give a reason and explicit timestamp bounds.",
              )}
            />
          </div>
        )}
        {step === 7 && (
          <Panel
            title={t("Review the complete input")}
            description={t(
              "Preliminary checks cover syntax and references. The local Python backend owns authoritative contract and calendar validation.",
            )}
          >
            <dl className="production-summary">
              {[
                ["Styles", rows(planning.styles).length],
                ["Orders", rows(planning.orders).length],
                ["Lines", rows(planning.lines).length],
                ["Profiles", rows(planning.capacity_profiles).length],
                ["Capabilities", rows(planning.capabilities).length],
                ["Shifts", rows(planning.shifts).length],
                ["Working dates", (calendar.working_dates as string[]).length],
                ["Assignments", rows(calendar.assignments).length],
                ["Planned stops", rows(calendar.planned_downtime).length],
                ["Unavailable periods", rows(calendar.unavailable_periods).length],
              ].map(([label, count]) => (
                <div key={String(label)}>
                  <dt>{textLabel(String(label))}</dt>
                  <dd>{count}</dd>
                </div>
              ))}
            </dl>
            {issues.length > 0 ? (
              <section className="production-issues" aria-label={t("Preliminary input issues")}>
                <p>{t("Resolve these errors before validation or export:")}</p>
                <ul>
                  {issues.map((issue) => (
                    <li key={`${textLabel(issue.path)}:${validationMessage(issue.message)}`}>
                      <strong>{textLabel(issue.path)}</strong>: {validationMessage(issue.message)}
                    </li>
                  ))}
                </ul>
              </section>
            ) : (
              <Notice>
                {t(
                  "Preliminary structure and references pass. Python still needs to check domain rules, break containment, calendar overlaps, profile dates and time offsets.",
                )}
              </Notice>
            )}
            <div className="production-validation" role="status">
              <Badge tone={receipt ? "teal" : "amber"}>
                {receipt ? t("PYTHON VALIDATED") : t("NOT AUTHORITATIVELY VALIDATED")}
              </Badge>
              {message && <p>{validationMessage(message)}</p>}
              {!api && (
                <p>
                  {t(
                    "Configure the local API to validate and activate. Offline import, editing and export remain available.",
                  )}
                </p>
              )}
            </div>
            {receipt && (
              <dl className="provenance-grid">
                <div className="full-width">
                  <dt>{t("Accepted instance fingerprint")}</dt>
                  <dd>
                    <code>{receipt.data.fingerprint}</code>
                  </dd>
                </div>
                <div>
                  <dt>{t("Validation request ID")}</dt>
                  <dd>
                    <code>{receipt.requestId}</code>
                  </dd>
                </div>
              </dl>
            )}
            <div className="panel-actions">
              <button
                type="button"
                className="button button-primary"
                disabled={!api || busy || editing || issues.length > 0}
                onClick={() => void validate()}
              >
                {busy ? t("Checking input…") : t("Validate with local Python")}
              </button>
              <button
                type="button"
                className="button"
                disabled={!receipt || !api || busy || editing}
                onClick={() => void activate()}
              >
                {t("Activate validated copy")}
              </button>
              <a className="button" href="/#/scheduling">
                {t("Open production scheduling")}
              </a>
              <a className="button" href="/#/capacity">
                {t("Open capacity assessment")}
              </a>
            </div>
            {dataset?.validatedFingerprint && (
              <p role="status">
                {t(
                  "Active workspace: your validated synthetic copy. Further draft edits require validation and activation again.",
                )}
              </p>
            )}
            <details className="details-block">
              <summary>{t("System-managed metadata & exact instance")}</summary>
              <p>
                {t(
                  "Schema 1 · whole-stage-minute-v1 · one-minute allocation · piece output · synthetic profile evidence. Internal IDs are generated for profiles, qualifications, assignments and stops. No exporter, benchmark, session or credential fields are included.",
                )}
              </p>
              <JsonBlock label={t("Exact synthetic scheduling instance")}>
                {encodeExact(draft)}
              </JsonBlock>
            </details>
          </Panel>
        )}
      </div>
      <div className="production-step-controls">
        <button
          type="button"
          className="button"
          disabled={step === 0 || editing || busy}
          onClick={() => setStep(step - 1)}
        >
          {t("Previous step")}
        </button>
        <button
          type="button"
          className="button button-primary"
          disabled={step === steps.length - 1 || editing || busy}
          onClick={() => setStep(step + 1)}
        >
          {t("Next step")}
        </button>
      </div>
    </div>
  );
}

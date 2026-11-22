import { isLosslessNumber } from "lossless-json";
import { type FormEvent, useId, useState } from "react";
import { stageName } from "../domain/exact";
import { type JsonObject, object, parseExact, text } from "../domain/json";
import {
  calendarOf,
  cloneInput,
  inspectInput,
  planningOf,
  rows,
  stages,
  WorkspaceInputError,
} from "../domain/production";
import { useProduction } from "../state/ProductionWorkspace";
import { Panel } from "./ui";

type Kind =
  | "styles"
  | "orders"
  | "lines"
  | "capacity_profiles"
  | "capabilities"
  | "shifts"
  | "assignments"
  | "planned_downtime"
  | "unavailable_periods";
interface Field {
  key: string;
  label: string;
  type?: "number" | "date" | "timestamp";
  choices?: { value: string; label: string }[];
  optional?: boolean;
  help?: string;
}
const identity: Record<Kind, string> = {
  styles: "style_id",
  orders: "order_id",
  lines: "line_id",
  capacity_profiles: "profile_id",
  capabilities: "capability_id",
  shifts: "shift_id",
  assignments: "assignment_id",
  planned_downtime: "downtime_id",
  unavailable_periods: "period_id",
};
const calendarKinds: Kind[] = ["assignments", "planned_downtime", "unavailable_periods"];
export const entityRows = (draft: JsonObject, kind: Kind) =>
  rows((calendarKinds.includes(kind) ? calendarOf(draft) : planningOf(draft))[kind]);
const valueText = (value: unknown) =>
  isLosslessNumber(value) ? value.value : typeof value === "string" ? value : "";
const newId = (kind: Kind) =>
  `${identity[kind].replace("_id", "")}-${crypto.randomUUID().slice(0, 8)}`;
function InputField({ field, value }: { field: Field; value: unknown }) {
  const id = useId();
  return (
    <div className="production-field">
      <label htmlFor={id}>{field.label}</label>
      {field.choices ? (
        <select id={id} name={field.key} defaultValue={valueText(value)} required={!field.optional}>
          <option value="">Choose explicitly</option>
          {field.choices.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={id}
          name={field.key}
          type={field.type === "date" ? "date" : "text"}
          inputMode={field.type === "number" ? "decimal" : undefined}
          defaultValue={valueText(value)}
          required={!field.optional}
          maxLength={field.type === "number" ? 128 : 4096}
          spellCheck={false}
          placeholder={field.type === "timestamp" ? "2030-01-07T08:00:00+03:00" : undefined}
        />
      )}
      {field.help && <small>{field.help}</small>}
    </div>
  );
}
const stageOptions = stages.map((value) => ({ value, label: stageName(value) }));
function RepeatedRows({ kind, initial }: { kind: "standards" | "breaks"; initial: JsonObject[] }) {
  const [items, setItems] = useState(() =>
    initial.map((item) => ({ key: crypto.randomUUID(), item })),
  );
  const fields: Field[] =
    kind === "standards"
      ? [
          { key: "standard-stage", label: "Supported stage", choices: stageOptions },
          { key: "standard-minutes", label: "Standard worker-minutes per piece", type: "number" },
        ]
      : [
          { key: "break-start", label: "Break start (with offset)", type: "timestamp" },
          { key: "break-end", label: "Break end (with offset)", type: "timestamp" },
        ];
  return (
    <fieldset className="production-repeater">
      <legend>{kind === "standards" ? "Stage labor standards" : "Explicit breaks"}</legend>
      <p className="field-help">
        {kind === "standards"
          ? "A positive standard describes worker labor per piece, not elapsed machine time. Add each supported stage once."
          : "No break rows explicitly means no breaks. Python checks containment and overlap; all times must be on the minute grid."}
      </p>
      {items.map(({ key, item }, i) => (
        <div className="production-repeat-row" key={key}>
          {fields.map((field, j) => (
            <InputField
              key={field.key}
              field={{ ...field, label: `${field.label} ${i + 1}` }}
              value={
                kind === "standards"
                  ? item[j === 0 ? "stage" : "standard_minutes_per_unit"]
                  : item[j === 0 ? "start" : "end"]
              }
            />
          ))}
          <button
            type="button"
            className="button"
            aria-label={`Remove ${kind === "standards" ? "standard" : "break"} ${i + 1}`}
            onClick={() => setItems(items.filter((x) => x.key !== key))}
          >
            Remove
          </button>
        </div>
      ))}
      <button
        type="button"
        className="button"
        disabled={items.length >= (kind === "standards" ? stages.length : 256)}
        onClick={() => setItems([...items, { key: crypto.randomUUID(), item: {} }])}
      >
        {kind === "standards" ? "Add stage standard" : "Add break"}
      </button>
    </fieldset>
  );
}
function OrderedStages({ initial }: { initial: string[] }) {
  const id = useId();
  const [selected, setSelected] = useState(initial);
  const [choice, setChoice] = useState("");
  return (
    <fieldset className="production-repeater">
      <legend>Ordered production stages</legend>
      <p className="field-help">
        Whole batches follow this exact sequence. Every stage needs a standard on the selected
        style.
      </p>
      <ol>
        {selected.map((stage, i) => (
          <li key={stage} className="production-stage">
            <input type="hidden" name="required-stage" value={stage} />
            <span>{stageName(stage)}</span>
            <button
              type="button"
              className="button button-small"
              aria-label={`Move stage ${i + 1} earlier`}
              disabled={i === 0}
              onClick={() => {
                const next = [...selected];
                [next[i - 1], next[i]] = [next[i] ?? "", next[i - 1] ?? ""];
                setSelected(next);
              }}
            >
              Earlier
            </button>
            <button
              type="button"
              className="button button-small"
              aria-label={`Move stage ${i + 1} later`}
              disabled={i === selected.length - 1}
              onClick={() => {
                const next = [...selected];
                [next[i], next[i + 1]] = [next[i + 1] ?? "", next[i] ?? ""];
                setSelected(next);
              }}
            >
              Later
            </button>
            <button
              type="button"
              className="button button-small"
              aria-label={`Remove stage ${i + 1}`}
              onClick={() => setSelected(selected.filter((_, n) => n !== i))}
            >
              Remove
            </button>
          </li>
        ))}
      </ol>
      <div className="production-field">
        <label htmlFor={id}>Add required stage</label>
        <select id={id} value={choice} onChange={(e) => setChoice(e.target.value)}>
          <option value="">Choose stage</option>
          {stages
            .filter((stage) => !selected.includes(stage))
            .map((stage) => (
              <option key={stage} value={stage}>
                {stageName(stage)}
              </option>
            ))}
        </select>
      </div>
      <button
        type="button"
        className="button"
        disabled={!choice}
        onClick={() => {
          setSelected([...selected, choice]);
          setChoice("");
        }}
      >
        Append stage
      </button>
    </fieldset>
  );
}
function RecordForm({
  kind,
  record,
  onSave,
  onCancel,
}: {
  kind: Kind;
  record: JsonObject | null;
  onSave: (value: JsonObject) => void;
  onCancel: () => void;
}) {
  const { draft } = useProduction();
  const [formError, setFormError] = useState<string | null>(null);
  const [selectedLine, setSelectedLine] = useState(() => valueText(record?.line_id));
  const p = planningOf(draft),
    calendar = calendarOf(draft);
  const choices = (collection: unknown, key: string, label?: (item: JsonObject) => string) =>
    rows(collection).map((item) => ({
      value: text(item[key]),
      label: label?.(item) ?? text(item[key]),
    }));
  const line: Field = {
    key: "line_id",
    label: "Production line",
    choices: choices(p.lines, "line_id"),
  };
  const id = identity[kind];
  const fields: Record<Kind, Field[]> = {
    styles: [{ key: id, label: "Style name / ID" }],
    orders: [
      { key: id, label: "Order ID" },
      { key: "style_id", label: "Product style", choices: choices(p.styles, "style_id") },
      { key: "quantity", label: "Quantity (pieces)", type: "number" },
      { key: "priority", label: "Priority (1 is highest)", type: "number" },
      { key: "release_date", label: "Release date", type: "date" },
      { key: "due_date", label: "Due date", type: "date" },
    ],
    lines: [
      { key: id, label: "Line name / ID" },
      { key: "stage", label: "Line stage", choices: stageOptions },
      {
        key: "worker_count",
        label: "Dedicated worker count",
        type: "number",
        help: "A whole number; zero is allowed and means zero labor capacity.",
      },
      {
        key: "availability",
        label: "Line availability",
        choices: [
          { value: "available", label: "Available" },
          { value: "unavailable", label: "Unavailable" },
        ],
      },
    ],
    capacity_profiles: [
      line,
      { key: "effective_date", label: "Profile effective date", type: "date" },
      {
        key: "assumed_efficiency",
        label: "Assumed efficiency (0–1)",
        type: "number",
        help: "Explicit synthetic capacity derating, not observed productivity or an ML prediction.",
      },
      { key: "source_id", label: "Synthetic assumption source" },
      {
        key: "evidence_reference",
        label: "Synthetic evidence reference (optional)",
        optional: true,
        help: "A text reference only; no URL or file is opened.",
      },
    ],
    capabilities: [
      line,
      { key: "style_id", label: "Qualified product style", choices: choices(p.styles, "style_id") },
      { key: "stage", label: "Qualified stage", choices: stageOptions },
      {
        key: "workforce_basis",
        label: "Synthetic crew qualification basis",
        help: "Explain why this dedicated crew is assumed qualified for this exact style and stage.",
      },
    ],
    shifts: [
      { key: id, label: "Shift name / ID" },
      { key: "start", label: "Shift start (with offset)", type: "timestamp" },
      { key: "end", label: "Shift end (with offset)", type: "timestamp" },
    ],
    assignments: [
      line,
      {
        key: "shift_id",
        label: "Declared shift",
        choices: choices(
          p.shifts,
          "shift_id",
          (s) => `${text(s.shift_id)} · ${text(object(s.interval).start)}`,
        ),
      },
      {
        key: "profile_id",
        label: "Capacity profile",
        choices: choices(
          rows(p.capacity_profiles).filter((profile) => profile.line_id === selectedLine),
          "profile_id",
          (s) =>
            `${text(s.line_id)} · ${text(s.effective_date)} · efficiency ${valueText(s.assumed_efficiency)} · ${text(s.profile_id)}`,
        ),
      },
    ],
    planned_downtime: [
      {
        key: "assignment_id",
        label: "Affected assignment",
        choices: choices(
          calendar.assignments,
          "assignment_id",
          (s) => `${text(s.line_id)} / ${text(s.shift_id)} · ${text(s.assignment_id)}`,
        ),
      },
      { key: "start", label: "Downtime start (with offset)", type: "timestamp" },
      { key: "end", label: "Downtime end (with offset)", type: "timestamp" },
      { key: "reason", label: "Downtime reason" },
    ],
    unavailable_periods: [
      line,
      { key: "start", label: "Unavailable start (with offset)", type: "timestamp" },
      { key: "end", label: "Unavailable end (with offset)", type: "timestamp" },
      { key: "reason", label: "Unavailability reason" },
    ],
  };
  const source = { ...record, ...(record?.interval ? object(record.interval) : {}) };
  const [internalId] = useState(() => record?.[id] ?? newId(kind));
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const data = new FormData(event.currentTarget);
      const get = (key: string) => String(data.get(key) ?? "");
      const result: JsonObject = { [id]: internalId };
      for (const field of fields[kind]) {
        const value = get(field.key);
        if (!field.optional || value)
          result[field.key] = field.type === "number" ? parseExact(value, 128) : value;
        else if (record && Object.hasOwn(record, field.key) && record[field.key] === null)
          result[field.key] = null;
      }
      if (kind === "styles") {
        result.output_unit = "piece";
        const minutes = data.getAll("standard-minutes");
        result.standards = data.getAll("standard-stage").map((value, i) => ({
          stage: String(value),
          standard_minutes_per_unit: parseExact(String(minutes[i] ?? ""), 128),
          measurement_unit: "worker_minutes_per_piece",
        }));
      }
      if (kind === "orders") result.required_stages = data.getAll("required-stage").map(String);
      if (kind === "capacity_profiles") result.evidence_status = "synthetic";
      if (["shifts", "planned_downtime", "unavailable_periods"].includes(kind)) {
        result.interval = { start: get("start"), end: get("end") };
        delete result.start;
        delete result.end;
      }
      if (kind === "shifts") {
        const ends = data.getAll("break-end");
        result.breaks = data
          .getAll("break-start")
          .map((start, i) => ({ start: String(start), end: String(ends[i] ?? "") }));
      }
      onSave(result);
    } catch (e) {
      setFormError(
        e instanceof WorkspaceInputError
          ? e.message
          : "Check the required fields and exact numeric syntax. No values were rounded or saved.",
      );
    }
  };
  return (
    <form
      onSubmit={submit}
      className="form-stack production-form"
      autoComplete="off"
      onChange={(event) => {
        const target = event.target;
        if (target instanceof HTMLSelectElement && target.name === "line_id")
          setSelectedLine(target.value);
      }}
    >
      <div className="production-field-grid">
        {fields[kind].map((field) => (
          <InputField
            key={field.key === "profile_id" ? `${field.key}:${selectedLine}` : field.key}
            field={field}
            value={field.key === id ? (record?.[id] ?? internalId) : source[field.key]}
          />
        ))}
      </div>
      {kind === "styles" && (
        <RepeatedRows kind="standards" initial={record ? rows(record.standards) : []} />
      )}
      {kind === "orders" && (
        <OrderedStages initial={record ? (record.required_stages as string[]) : []} />
      )}
      {kind === "shifts" && (
        <RepeatedRows kind="breaks" initial={record ? rows(record.breaks) : []} />
      )}
      {formError && (
        <p className="error-notice" role="alert">
          {formError}
        </p>
      )}
      <div className="panel-actions">
        <button type="submit" className="button button-primary">
          Save record
        </button>
        <button type="button" className="button" onClick={onCancel}>
          Cancel editing
        </button>
      </div>
    </form>
  );
}
export function EntitySection({
  kind,
  title,
  description,
}: {
  kind: Kind;
  title: string;
  description: string;
}) {
  const { draft, replace, invalidate, editing, setEditing } = useProduction();
  const [selected, setSelected] = useState<number | "new" | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const collection = entityRows(draft, kind);
  const close = () => {
    setSelected(null);
    setEditing(false);
    setFeedback(null);
  };
  const save = (record: JsonObject) => {
    if (collection.some((r, i) => i !== selected && r[identity[kind]] === record[identity[kind]]))
      throw new WorkspaceInputError("This identifier is already used. Choose a unique name / ID.");
    const next = cloneInput(draft),
      container = calendarKinds.includes(kind) ? calendarOf(next) : planningOf(next),
      records = rows(container[kind]);
    if (selected === "new") records.push(record);
    else if (selected !== null) records[selected] = record;
    // Drafts may remain incomplete. Reject new local errors inside this record;
    // cross-record errors stay visible so references can be repaired deliberately.
    const prefix = `Instance.planning.${calendarKinds.includes(kind) ? "calendar." : ""}${kind}[${selected === "new" ? records.length - 1 : selected}]`;
    const local = inspectInput(next).find((e) => e.path.startsWith(prefix));
    if (local) throw new WorkspaceInputError(local.message);
    replace(next);
    close();
  };
  const remove = (index: number) => {
    const next = cloneInput(draft),
      container = calendarKinds.includes(kind) ? calendarOf(next) : planningOf(next);
    rows(container[kind]).splice(index, 1);
    replace(next);
    setFeedback(
      "Record removed. Check references in Review; dependent records are retained for explicit repair.",
    );
  };
  const summary = (r: JsonObject) =>
    kind === "orders"
      ? `${valueText(r.quantity)} pieces · ${text(r.style_id)}`
      : kind === "lines"
        ? `${stageName(text(r.stage))} · ${valueText(r.worker_count)} workers`
        : kind === "capacity_profiles"
          ? `${text(r.line_id)} · ${text(r.effective_date)} · efficiency ${valueText(r.assumed_efficiency)}`
          : kind === "capabilities"
            ? `${text(r.line_id)} / ${text(r.style_id)} / ${stageName(text(r.stage))}`
            : kind === "assignments"
              ? `${text(r.line_id)} / ${text(r.shift_id)}`
              : kind === "shifts"
                ? `${text(object(r.interval).start)} to ${text(object(r.interval).end)}`
                : kind === "styles"
                  ? rows(r.standards)
                      .map(
                        (s) =>
                          `${stageName(text(s.stage))}: ${valueText(s.standard_minutes_per_unit)}`,
                      )
                      .join(" · ")
                  : text(r.reason);
  return (
    <Panel title={title} description={description}>
      {collection.length === 0 && (
        <p className="field-help">
          No {title.toLowerCase()} declared. Add records with explicit synthetic assumptions.
        </p>
      )}
      <ul className="production-records">
        {collection.map((record, index) => (
          <li key={text(record[identity[kind]])}>
            <div>
              <strong>{text(record[identity[kind]])}</strong>
              <p>{summary(record)}</p>
            </div>
            <div className="panel-actions">
              <button
                type="button"
                className="button button-small"
                disabled={editing}
                aria-label={`Edit ${text(record[identity[kind]])}`}
                onClick={() => {
                  invalidate();
                  setSelected(index);
                  setEditing(true);
                }}
              >
                Edit
              </button>
              <button
                type="button"
                className="button button-small"
                disabled={editing}
                aria-label={`Remove ${text(record[identity[kind]])}`}
                onClick={() => remove(index)}
              >
                Remove
              </button>
            </div>
          </li>
        ))}
      </ul>
      {selected === null ? (
        <button
          type="button"
          className="button"
          disabled={editing || collection.length >= 256}
          onClick={() => {
            invalidate();
            setSelected("new");
            setEditing(true);
          }}
        >
          Add {title.toLowerCase().replace(/ies$/, "y").replace(/s$/, "")}
        </button>
      ) : (
        <RecordForm
          key={String(selected)}
          kind={kind}
          record={selected === "new" ? null : (collection[selected] ?? null)}
          onSave={save}
          onCancel={close}
        />
      )}
      {feedback && <p role="status">{feedback}</p>}
    </Panel>
  );
}
export function WorkingDates() {
  const { draft, replace } = useProduction();
  const [date, setDate] = useState("");
  const dates = calendarOf(draft).working_dates as string[];
  return (
    <Panel
      title="Working dates"
      description="Declare each shift start date explicitly. Overnight shifts belong to their start date; no weekly calendar is inferred."
    >
      <div className="production-dates">
        {dates.map((date, index) => (
          <span key={date}>
            {date}
            <button
              type="button"
              className="button button-small"
              aria-label={`Remove working date ${date}`}
              onClick={() => {
                const next = cloneInput(draft);
                (calendarOf(next).working_dates as string[]).splice(index, 1);
                replace(next);
              }}
            >
              Remove
            </button>
          </span>
        ))}
      </div>
      <form
        className="production-date-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!date || dates.includes(date)) return;
          const next = cloneInput(draft);
          (calendarOf(next).working_dates as string[]).push(date);
          replace(next);
          setDate("");
        }}
      >
        <label>
          Working date
          <input
            type="date"
            required
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        </label>
        <button
          type="submit"
          className="button"
          disabled={!date || dates.includes(date) || dates.length >= 256}
        >
          Add working date
        </button>
      </form>
      {dates.includes(date) && <p role="status">This working date is already declared.</p>}
    </Panel>
  );
}

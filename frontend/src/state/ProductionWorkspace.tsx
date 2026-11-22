import { createContext, type ReactNode, useContext, useEffect, useRef, useState } from "react";
import { ApiError, type ApiResult, validationGuidance } from "../api/client";
import { encodeExact, type JsonObject } from "../domain/json";
import {
  cloneInput,
  type InputValidation,
  inspectInput,
  newInput,
  userDataset,
  WorkspaceInputError,
} from "../domain/production";
import { useWorkspace } from "./Workspace";

interface Value {
  draft: JsonObject;
  replace: (next: JsonObject) => void;
  invalidate: () => void;
  step: number;
  setStep: (value: number) => void;
  editing: boolean;
  setEditing: (value: boolean) => void;
  receipt: ApiResult<InputValidation> | null;
  busy: boolean;
  message: string | null;
  validate: () => Promise<void>;
  activate: () => Promise<void>;
}
const Context = createContext<Value | null>(null);
export function ProductionProvider({ children }: { children: ReactNode }) {
  const { api, sessionId, dataset, capabilities, activateDataset, rejectSession } = useWorkspace();
  const [draft, setDraft] = useState(newInput);
  const [step, setStep] = useState(0);
  const [editing, setEditing] = useState(false);
  const [receipt, setReceipt] = useState<ApiResult<InputValidation> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const current = useRef(draft),
    serial = useRef(0),
    pending = useRef<AbortController | null>(null);
  const accepted = useRef<{
    source: string;
    session: number;
    owner: string;
    receipt: ApiResult<InputValidation>;
  } | null>(null);
  const owner = `${sessionId}:${dataset?.key ?? "empty"}`;
  const ownership = useRef(owner);
  ownership.current = owner;
  const activating = useRef(false);
  const invalidate = () => {
    serial.current++;
    pending.current?.abort();
    pending.current = null;
    accepted.current = null;
    activating.current = false;
    setReceipt(null);
    setBusy(false);
    setMessage(null);
  };
  useEffect(() => {
    if (ownership.current !== owner) return;
    serial.current++;
    pending.current?.abort();
    pending.current = null;
    accepted.current = null;
    setReceipt(null);
    setBusy(false);
    setMessage(
      "Dataset or session changed. Validate the draft again; earlier server jobs may continue.",
    );
    return () => {
      serial.current++;
      pending.current?.abort();
    };
  }, [owner]);
  const replace = (next: JsonObject) => {
    invalidate();
    const copy = cloneInput(next);
    current.current = copy;
    setDraft(copy);
  };
  const validate = async () => {
    if (!api || pending.current || activating.current || editing) return;
    const issues = inspectInput(current.current, capabilities);
    if (issues.length) {
      setMessage("Resolve preliminary errors before backend validation.");
      return;
    }
    const source = encodeExact(current.current),
      stamp = ++serial.current;
    accepted.current = null;
    setReceipt(null);
    setMessage(null);
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    try {
      const result = await api.validateInput(cloneInput(current.current), controller.signal);
      if (
        controller.signal.aborted ||
        stamp !== serial.current ||
        owner !== ownership.current ||
        source !== encodeExact(current.current)
      )
        return;
      accepted.current = { source, session: sessionId, owner, receipt: result };
      setReceipt(result);
      setMessage(
        "Python accepted the complete synthetic input. Scheduling feasibility has not been assessed.",
      );
    } catch (e) {
      if (stamp !== serial.current || controller.signal.aborted) return;
      const error = e instanceof ApiError ? e : new ApiError("contract");
      setMessage(
        error.domainCode ? (validationGuidance[error.domainCode] ?? error.message) : error.message,
      );
      rejectSession(error);
    } finally {
      if (stamp === serial.current) {
        pending.current = null;
        setBusy(false);
      }
    }
  };
  const activate = async () => {
    const checked = accepted.current;
    if (
      !api ||
      busy ||
      activating.current ||
      editing ||
      !checked ||
      checked.session !== sessionId ||
      checked.owner !== owner ||
      checked.source !== encodeExact(current.current)
    )
      return;
    const stamp = serial.current;
    activating.current = true;
    setBusy(true);
    try {
      const next = await userDataset(current.current, checked.receipt.data);
      if (stamp !== serial.current || accepted.current !== checked) return;
      activateDataset(next);
      setMessage("Validated copy activated. Open Production scheduling to run the reference.");
    } catch (e) {
      if (stamp === serial.current)
        setMessage(e instanceof WorkspaceInputError ? e.message : "Unable to activate this draft.");
    } finally {
      if (stamp === serial.current) {
        activating.current = false;
        setBusy(false);
      }
    }
  };
  return (
    <Context.Provider
      value={{
        draft,
        replace,
        invalidate,
        step,
        setStep,
        editing,
        setEditing,
        receipt,
        busy,
        message,
        validate,
        activate,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useProduction(): Value {
  const value = useContext(Context);
  if (!value) throw new Error("ProductionProvider is required.");
  return value;
}

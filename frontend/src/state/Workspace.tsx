import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { ApiClient, ApiError } from "../api/client";
import { datasets } from "../demo/catalog";
import type { Capabilities, CapacityReport, Dataset, ScheduleReport } from "../domain/models";

type Mode = "preview" | "api";
type Status = "disconnected" | "loading" | "connected" | "error";
interface WorkspaceValue {
  catalog: readonly Dataset[];
  dataset: Dataset | null;
  mode: Mode;
  status: Status;
  origin: string | null;
  capacity: CapacityReport | null;
  schedule: ScheduleReport | null;
  scheduleLoading: boolean;
  scheduleError: ApiError | null;
  capabilities: Capabilities | null;
  health: { status: "ok"; version: "v1" } | null;
  requestId: string | null;
  error: ApiError | null;
  selectDataset: (key: string) => void;
  connect: (origin: string, token: string) => Promise<void>;
  enterPreview: () => void;
  refresh: () => void;
  loadSchedule: () => Promise<void>;
}
const Context = createContext<WorkspaceValue | null>(null);
const asError = (error: unknown) => (error instanceof ApiError ? error : new ApiError("contract"));

export function WorkspaceProvider({
  children,
  catalog = datasets,
}: {
  children: ReactNode;
  catalog?: readonly Dataset[];
}) {
  const [dataset, setDataset] = useState<Dataset | null>(catalog[0] ?? null);
  const [mode, setMode] = useState<Mode>("preview");
  const [status, setStatus] = useState<Status>("disconnected");
  const [origin, setOrigin] = useState<string | null>(null);
  const [capacity, setCapacity] = useState<CapacityReport | null>(dataset?.previewCapacity ?? null);
  const [schedule, setSchedule] = useState<ScheduleReport | null>(null);
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleError, setScheduleError] = useState<ApiError | null>(null);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [health, setHealth] = useState<WorkspaceValue["health"]>(null);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const client = useRef<ApiClient | null>(null);
  const selected = useRef(dataset);
  const generation = useRef(0);

  useEffect(
    () => () => {
      generation.current++;
      client.current?.disconnect();
      client.current = null;
    },
    [],
  );

  const clearSchedule = () => {
    setSchedule(null);
    setScheduleError(null);
    setScheduleLoading(false);
  };
  const fetchCapacity = useCallback(async (api: ApiClient, source: Dataset, stamp: number) => {
    setStatus("loading");
    setCapacity(null);
    setError(null);
    setRequestId(null);
    try {
      const result = await api.capacity(source.planning);
      if (stamp !== generation.current) return;
      setCapacity(result.data);
      setRequestId(result.requestId);
      setStatus("connected");
    } catch (failure) {
      if (stamp !== generation.current) return;
      setError(asError(failure));
      setStatus("error");
    }
  }, []);

  const selectDataset = (key: string) => {
    const next = catalog.find((item) => item.key === key);
    if (!next || next === dataset) return;
    const stamp = ++generation.current;
    selected.current = next;
    setDataset(next);
    clearSchedule();
    setError(null);
    setRequestId(null);
    if (mode === "preview") {
      setCapacity(next.previewCapacity);
      return;
    }
    setCapacity(null);
    if (client.current && health) void fetchCapacity(client.current, next, stamp);
  };
  const enterPreview = () => {
    generation.current++;
    client.current?.disconnect();
    client.current = null;
    setMode("preview");
    setStatus("disconnected");
    setOrigin(null);
    setHealth(null);
    setCapabilities(null);
    setError(null);
    setRequestId(null);
    clearSchedule();
    setCapacity(dataset?.previewCapacity ?? null);
  };
  const connect = async (address: string, token: string) => {
    generation.current++;
    client.current?.disconnect();
    client.current = null;
    setMode("api");
    setStatus("loading");
    setOrigin(null);
    setCapacity(null);
    setHealth(null);
    setCapabilities(null);
    setError(null);
    setRequestId(null);
    clearSchedule();
    let api: ApiClient | null = null;
    try {
      api = new ApiClient(address, token);
      client.current = api;
      const checkedHealth = await api.health();
      const checkedCapabilities = await api.capabilities();
      if (client.current !== api) return;
      setOrigin(api.origin);
      setHealth(checkedHealth.data);
      setCapabilities(checkedCapabilities.data);
      if (selected.current) await fetchCapacity(api, selected.current, ++generation.current);
      else setStatus("connected");
    } catch (failure) {
      if (client.current !== api) return;
      client.current?.disconnect();
      client.current = null;
      setError(asError(failure));
      setStatus("error");
    }
  };
  const refresh = () => {
    if (!client.current || !dataset) return;
    const stamp = ++generation.current;
    clearSchedule();
    void fetchCapacity(client.current, dataset, stamp);
  };
  const loadSchedule = async () => {
    if (!dataset?.instance || !dataset.savedProposal) return;
    const stamp = generation.current;
    setScheduleLoading(true);
    setScheduleError(null);
    setSchedule(null);
    try {
      if (mode === "preview") setSchedule(dataset.previewSchedule);
      else {
        if (!client.current) throw new ApiError("authentication");
        const result = await client.current.verify(dataset.instance, dataset.savedProposal);
        if (stamp !== generation.current) return;
        setSchedule(result.data);
      }
    } catch (failure) {
      if (stamp === generation.current) setScheduleError(asError(failure));
    } finally {
      if (stamp === generation.current) setScheduleLoading(false);
    }
  };
  return (
    <Context.Provider
      value={{
        catalog,
        dataset,
        mode,
        status,
        origin,
        capacity,
        schedule,
        scheduleLoading,
        scheduleError,
        capabilities,
        health,
        requestId,
        error,
        selectDataset,
        connect,
        enterPreview,
        refresh,
        loadSchedule,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useWorkspace(): WorkspaceValue {
  const value = useContext(Context);
  if (!value) throw new Error("WorkspaceProvider is required.");
  return value;
}

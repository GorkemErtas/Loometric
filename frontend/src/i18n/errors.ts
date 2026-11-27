import type { ApiFailure } from "../api/client";
import type { MessageKey } from "./translate";

export const apiFailureMessages = {
  network: "The local backend is unreachable. Check the server and configured origin.",
  authentication: "The local session was rejected. Check the Bearer token and allowed origin.",
  validation: "The backend rejected this input. No capacity or schedule result was accepted.",
  busy: "The local execution slots are busy. Wait briefly and retry.",
  timeout: "The bounded request reached its deadline. Retry when the local backend is ready.",
  contract: "The backend response does not match the supported API contract.",
  server: "The backend could not complete this request. No replacement result was invented.",
  cancelled: "The local request was cancelled.",
  missing:
    "The job is missing. Its record may have expired or the local server may have restarted.",
  expired: "The server's volatile result retention has expired. No result is available.",
  not_ready: "The job result is unavailable in its current state. Inspect its actual status.",
} as const satisfies Record<ApiFailure, MessageKey>;

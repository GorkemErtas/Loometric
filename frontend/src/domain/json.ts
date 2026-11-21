import { isLosslessNumber, parse, stringify } from "lossless-json";

export type JsonObject = Record<string, unknown>;
export class ContractError extends Error {
  constructor() {
    super("The loaded data does not match the supported synthetic contract.");
  }
}

export function object(value: unknown): JsonObject {
  if (value === null || typeof value !== "object" || Array.isArray(value))
    throw new ContractError();
  return value as JsonObject;
}
export function list(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new ContractError();
  return value;
}
export function text(value: unknown): string {
  if (typeof value !== "string") throw new ContractError();
  return value;
}
export function flag(value: unknown): boolean {
  if (typeof value !== "boolean") throw new ContractError();
  return value;
}
export const texts = (value: unknown) => list(value).map(text);

export function parseExact(source: string, maxBytes = 2 * 1024 * 1024 + 1024): unknown {
  if (new TextEncoder().encode(source).length > maxBytes) throw new ContractError();
  // Guard recursion before the library parser; strings and escaped quotes are opaque.
  let quoted = false;
  let escaped = false;
  let depth = 0;
  for (const char of source) {
    if (quoted) {
      if (escaped) escaped = false;
      else if (char === "\\") escaped = true;
      else if (char === '"') quoted = false;
    } else if (char === '"') quoted = true;
    else if (char === "{" || char === "[") {
      if (++depth > 24) throw new ContractError();
    } else if (char === "}" || char === "]") depth--;
  }
  try {
    return parse(source, null, {
      onDuplicateKey: () => {
        throw new ContractError();
      },
    });
  } catch {
    throw new ContractError();
  }
}

export function encodeExact(value: unknown): string {
  const result = stringify(value);
  if (result === undefined) throw new ContractError();
  return result;
}

export function integer(value: unknown): string {
  if (
    !isLosslessNumber(value) ||
    !/^(0|[1-9][0-9]*)$/.test(value.value) ||
    value.value.length > 128
  ) {
    throw new ContractError();
  }
  return value.value;
}

export function decimal(value: unknown): string {
  const result = typeof value === "string" ? value : isLosslessNumber(value) ? value.value : "";
  const match = /^(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d{1,3}))?$/.exec(result);
  if (!match || result.length > 256 || Math.abs(Number(match[3] ?? "0")) > 100)
    throw new ContractError();
  return result;
}

export function nullableDecimal(value: unknown): string | null {
  return value === null ? null : decimal(text(value));
}
export function inputDecimal(value: unknown): string {
  if (!isLosslessNumber(value)) throw new ContractError();
  return decimal(value);
}
export const reportedDecimal = (value: unknown) => decimal(text(value));

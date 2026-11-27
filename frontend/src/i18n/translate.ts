import type { Locale } from "./locale";
import { messages } from "./messages";

// English source messages are stable, typed IDs. Placeholders must be supplied;
// Turkish can reorder them without concatenating translated sentence fragments.
export type MessageKey = keyof typeof messages;
type Placeholders<S extends string> = S extends `${string}{${infer P}}${infer Rest}`
  ? P | Placeholders<Rest>
  : never;
export type MessageParameters<K extends MessageKey> = [Placeholders<K>] extends [never]
  ? []
  : [values: Record<Placeholders<K>, string | number>];

export function translate<K extends MessageKey>(
  locale: Locale,
  key: K,
  ...parameters: MessageParameters<K>
): string {
  const template: string = locale === "tr-TR" ? messages[key] : key;
  const values = parameters[0] as Record<string, string | number> | undefined;
  // One pass: user text is never interpreted again as a placeholder or markup.
  return template.replace(/\{(\w+)\}/g, (match, name: string) =>
    values && Object.hasOwn(values, name) ? String(values[name]) : match,
  );
}

export function hasMessage(value: string): value is MessageKey {
  return Object.hasOwn(messages, value);
}

// For trusted frontend metadata and existing validator messages. Never apply
// this to free-text user assumptions, IDs, exports, tokens or raw server errors.
export function localizeLabel(locale: Locale, value: string): string {
  return hasMessage(value) ? (locale === "tr-TR" ? messages[value] : value) : value;
}

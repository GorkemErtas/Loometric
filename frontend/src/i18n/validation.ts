import type { Locale } from "./locale";
import { messages } from "./messages";
import { hasMessage, localizeLabel } from "./translate";

const templates = [
  "{p0} requires a {p1} from {p2} to {p3}.",
  "{p0} must be nonblank canonical text without control characters.",
  "Unsupported HTTP instance: {p0} orders / {p1} operations exceed the published envelope (at most 32 / 96). Inputs are never truncated.",
] as const;

// Only these existing frontend validation templates are matched. Arbitrary API
// error bodies are never passed here, logged, interpolated as HTML or persisted.
export function validationMessage(locale: Locale, value: string): string {
  if (hasMessage(value)) return localizeLabel(locale, value);
  for (const template of templates) {
    const chunks = template.split(/\{p\d+\}/);
    const expression = new RegExp(
      `^${chunks.map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("(.+?)")}$`,
    );
    const match = expression.exec(value);
    if (match) {
      const pattern = locale === "tr-TR" ? messages[template] : template;
      return pattern.replace(/\{p(\d+)\}/g, (_, index: string) =>
        localizeLabel(locale, match[Number(index) + 1] ?? ""),
      );
    }
  }
  // Import errors retain their exact diagnostic path, with translated guidance.
  const split = value.indexOf(": ");
  if (split > 0 && hasMessage(value.slice(split + 2))) {
    return `${localizeLabel(locale, value.slice(0, split))}: ${localizeLabel(locale, value.slice(split + 2))}`;
  }
  return value;
}

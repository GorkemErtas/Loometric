export const locales = ["tr-TR", "en-US"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "tr-TR";
export const languageStorageKey = "loometric.language";
export const isLocale = (value: unknown): value is Locale =>
  locales.some((locale) => locale === value);

export function readLocale(): Locale {
  try {
    const stored = localStorage.getItem(languageStorageKey);
    return isLocale(stored) ? stored : defaultLocale;
  } catch {
    return defaultLocale;
  }
}

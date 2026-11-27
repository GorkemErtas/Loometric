import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";
import {
  clockLabel,
  dateLabel,
  formatExact,
  formatSignedExact,
  percentExact,
  percentValueExact,
} from "../domain/exact";
import { codeLabels } from "./codes";
import { formValidation, localizeValidity } from "./formValidation";
import { defaultLocale, type Locale, languageStorageKey, readLocale } from "./locale";
import { localizeLabel, type MessageKey, type MessageParameters, translate } from "./translate";
import { validationMessage } from "./validation";

export function createI18n(locale: Locale) {
  function t<K extends MessageKey>(key: K, ...parameters: MessageParameters<K>) {
    const values = parameters[0];
    const localized = values
      ? [
          Object.fromEntries(
            Object.entries(values).map(([key, value]) => [
              key,
              typeof value === "number" ? new Intl.NumberFormat(locale).format(value) : value,
            ]),
          ),
        ]
      : [];
    return translate(locale, key, ...(localized as MessageParameters<K>));
  }
  const label = (value: string) => localizeLabel(locale, value);
  const codeLabel = (value: string) => {
    if (value.startsWith("OUTSIDE_TRAINING_SUPPORT:")) {
      const feature = value.slice("OUTSIDE_TRAINING_SUPPORT:".length);
      const key = Object.hasOwn(codeLabels, feature)
        ? codeLabels[feature as keyof typeof codeLabels]
        : null;
      return t("Outside training support: {p0}", { p0: key ? label(key) : feature });
    }
    const key = Object.hasOwn(codeLabels, value)
      ? codeLabels[value as keyof typeof codeLabels]
      : null;
    return key ? label(key) : `${label("Unrecognized status")} (${value})`;
  };
  const number = (value: number, decimals?: number) =>
    new Intl.NumberFormat(
      locale,
      decimals === undefined
        ? {}
        : {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
          },
    ).format(value);
  const percent = (value: number, decimals = 2) =>
    new Intl.NumberFormat(locale, {
      style: "percent",
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  return {
    locale,
    t,
    label,
    codeLabel,
    number,
    percent,
    formValidation: formValidation(locale),
    validationMessage: (value: string) => validationMessage(locale, value),
    backendText: (value: string) => localizeLabel(locale, value),
    stageName: codeLabel,
    formatExact: (value: string) => formatExact(value, locale),
    formatSignedExact: (value: string) => formatSignedExact(value, locale),
    percentExact: (value: string) => percentExact(value, locale),
    percentValueExact: (value: string) => percentValueExact(value, locale),
    dateLabel: (value: string) => dateLabel(value, locale),
    clockLabel: (value: string) => clockLabel(value, locale),
    ratio: (value: number | null) => (value === null ? label("Abstained") : number(value, 5)),
    metricText: (value: string | null, unit: string) =>
      value === null
        ? label("Not applicable")
        : unit === "ratio"
          ? percentExact(value, locale)
          : formatSignedExact(value, locale),
  };
}

type I18n = ReturnType<typeof createI18n> & { setLocale: (locale: Locale) => void };
const Context = createContext<I18n | null>(null);
export function I18nProvider({
  children,
  initialLocale,
}: {
  children: ReactNode;
  initialLocale?: Locale;
}) {
  const [locale, setLanguage] = useState<Locale>(() => initialLocale ?? readLocale());
  useEffect(() => {
    document.documentElement.lang = locale;
    document
      .querySelector<HTMLMetaElement>('meta[name="description"]')
      ?.setAttribute(
        "content",
        translate(locale, "Local synthetic garment planning inspection. No live factory data."),
      );
    for (const target of document.querySelectorAll<
      HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
    >("[data-localized-validity]"))
      localizeValidity(target, locale);
  }, [locale]);
  const value = useMemo(
    () => ({
      ...createI18n(locale),
      setLocale: (next: Locale) => {
        setLanguage(next);
        try {
          localStorage.setItem(languageStorageKey, next);
        } catch {
          /* Memory-only preference if storage is unavailable. */
        }
      },
    }),
    [locale],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useI18n(): I18n {
  const value = useContext(Context);
  if (!value) throw new Error("I18nProvider is required.");
  return value;
}

export { defaultLocale };

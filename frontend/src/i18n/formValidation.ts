import type { FormEvent } from "react";
import type { Locale } from "./locale";
import { translate } from "./translate";

type Control = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
const control = (target: EventTarget | null): target is Control =>
  target instanceof HTMLInputElement ||
  target instanceof HTMLTextAreaElement ||
  target instanceof HTMLSelectElement;

export function localizeValidity(target: Control, locale: Locale) {
  target.setCustomValidity("");
  const v = target.validity;
  const key = v.valueMissing
    ? "Complete this required field."
    : v.typeMismatch
      ? "Enter a valid value in the requested format."
      : v.rangeOverflow || v.rangeUnderflow
        ? "Enter a value within the displayed limits."
        : v.tooLong || v.tooShort
          ? "Check the required text length."
          : v.patternMismatch
            ? "Use the requested format and allowed characters."
            : v.stepMismatch || v.badInput
              ? "Enter a valid number with the required precision."
              : null;
  target.setCustomValidity(key ? translate(locale, key) : "");
  if (key) target.dataset.localizedValidity = "true";
  else delete target.dataset.localizedValidity;
}

export function formValidation(locale: Locale) {
  return {
    onInvalidCapture: (event: FormEvent<HTMLFormElement>) => {
      if (control(event.target)) localizeValidity(event.target, locale);
    },
    onInputCapture: (event: FormEvent<HTMLFormElement>) => {
      if (control(event.target)) {
        event.target.setCustomValidity("");
        delete event.target.dataset.localizedValidity;
      }
    },
  };
}

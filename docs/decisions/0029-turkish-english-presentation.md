# ADR 0029: Typed Turkish and English presentation

Status: accepted for final dashboard localization, 2026-11-27.

## Context and options

The local dashboard needs complete Turkish and English presentation without changing
planning arithmetic, ML behavior, wire contracts or credential ownership. Options were
a new i18n dependency, runtime DOM replacement, or a small typed catalog and React
context using the existing stack. Choose the catalog and context: two bundled locales
need no network loading or new dependency, and translation remains explicit in React.

## Decision

Use `tr-TR` by default and selectable `en-US`. English source messages serve as typed
catalog keys; each has a Turkish translation. TypeScript checks message keys and
required interpolation arguments. Whole messages can reorder placeholders, and
interpolation runs once as React text. Never interpret translated content as HTML.
Static frontend metadata uses the same catalog at rendering time. Existing validator
templates are translated through a narrowly declared presentation adapter; validator
and calculation behavior remains independent of language.

Put the provider above the page workspace without a locale-based component key.
Switching language changes text, accessible names, document language/title and
formatters while keeping the mounted session, draft, requests and results. The
header's keyboard-accessible TR/EN buttons remain available on mobile.

Store only the supported locale string in `localStorage["loometric.language"]`, only
after explicit selection. Invalid/unavailable storage falls back to Turkish; failed
writes leave switching usable in memory. Tokens, origins, inputs, results and jobs
retain their existing memory-only boundaries. No sessionStorage, cookies or external
service is introduced.

Map backend status/error/reason codes to frontend messages without changing codes,
request payloads or accepted response contracts. Keep model names, identifiers,
fingerprints, policies, user-authored text and machine-readable JSON unchanged.
Known bundled demo descriptions may be translated; user input is never translated.
Remove obsolete milestone prefixes from screen copy while retaining scientific
experiment IDs, provenance and NO_ML_PROMOTION.

Use `Intl` for display. Exact planning decimals retain BigInt grouping and their
complete fractional digits; they never pass through Number. Percent placement and
separators come from Intl. Dates and times preserve the source wall clock and explicit
offset instead of converting through the browser timezone. The separate ML float
contract uses locale-aware fixed precision. Input controls and JSON retain their
original canonical numeric/date syntax.

## Consequences and verification

The catalog is bundled for offline use. New UI messages require a catalog entry;
changes to an English source key update its callers and Turkish translation together.
Tests check placeholders, UTF-8, static metadata, code mappings, precision, persistence,
storage failures, switching, validation and exact exports. Real-browser checks cover
both locales on desktop/mobile and all five unchanged experimental models.

Table scroll regions establish a containing block so absolutely positioned
screen-reader labels remain within their scroll region on narrow screens. Notice
links retain the teal palette with sufficient contrast against the tinted background.

No backend, model artifact, feature schema, resource policy or calculation is changed.
The project remains local-only; no deployment or operational ML promotion is implied.

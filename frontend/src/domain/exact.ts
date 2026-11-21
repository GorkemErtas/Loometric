// Presentation arithmetic only: sums of unique report slots and exact display.
// Calendar, efficiency, potential output and feasibility calculations stay in Python.
function parts(value: string): { digits: bigint; scale: number } {
  const [coefficient = "0", exponent = "0"] = value.toLowerCase().split("e");
  const [whole = "0", fraction = ""] = coefficient.split(".");
  const scale = fraction.length - Number(exponent); // Bounded exponent metadata, not the value.
  return scale < 0
    ? { digits: BigInt(whole + fraction) * 10n ** BigInt(-scale), scale: 0 }
    : { digits: BigInt(whole + fraction), scale };
}
function fromParts(digits: bigint, scale: number): string {
  const raw = digits.toString().padStart(scale + 1, "0");
  return scale ? `${raw.slice(0, -scale)}.${raw.slice(-scale)}`.replace(/\.?0+$/, "") : raw;
}
export function sumExact(values: readonly string[]): string {
  const numbers = values.map(parts);
  const scale = Math.max(0, ...numbers.map((n) => n.scale));
  return fromParts(
    numbers.reduce((sum, n) => sum + n.digits * 10n ** BigInt(scale - n.scale), 0n),
    scale,
  );
}
export function formatExact(value: string): string {
  const parsed = parts(value);
  const [whole = "0", fraction] = fromParts(parsed.digits, parsed.scale).split(".");
  return BigInt(whole).toLocaleString("en-US") + (fraction ? `.${fraction}` : "");
}
export function percentExact(value: string): string {
  const parsed = parts(value);
  return `${formatExact(fromParts(parsed.digits * 100n, parsed.scale))}%`;
}
export function compareExact(a: string, b: string): number {
  const left = parts(a);
  const right = parts(b);
  const scale = Math.max(left.scale, right.scale);
  const x = left.digits * 10n ** BigInt(scale - left.scale);
  const y = right.digits * 10n ** BigInt(scale - right.scale);
  return x < y ? -1 : x > y ? 1 : 0;
}
export function visualPercent(value: string, denominator: string): string {
  const a = parts(value);
  const b = parts(denominator);
  if (b.digits === 0n) return "0%";
  const scale = Math.max(a.scale, b.scale);
  const basisPoints =
    (a.digits * 10n ** BigInt(scale - a.scale) * 10000n) /
    (b.digits * 10n ** BigInt(scale - b.scale));
  // Only a bounded layout integer becomes Number. Exact values remain in text.
  return `${Number(basisPoints > 10000n ? 10000n : basisPoints) / 100}%`;
}
export const stageName = (stage: string) =>
  stage.replaceAll("_", " ").replace(/^./, (s) => s.toUpperCase());
export function dateLabel(date: string): string {
  const [year, month, day] = date.slice(0, 10).split("-");
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  return `${day} ${months[Number(month) - 1] ?? month} ${year}`;
}
export const clockLabel = (value: string) =>
  `${dateLabel(value)}, ${value.slice(11, 16)} ${value.slice(19)}`;

export const formatSignedExact = (value: string) =>
  value.startsWith("-") ? `-${formatExact(value.slice(1))}` : formatExact(value);

const numberFormatter = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
export const MAX_SAFE_PAISE = Number.MAX_SAFE_INTEGER;

function roundMagnitude(value: number): number { return Math.sign(value) * Math.round(Math.abs(value)); }

export function toPaise(value: string): number {
  const clean = value.replace(/,/g, "").trim();
  if (!/^\d+(\.\d{0,2})?$/.test(clean)) throw new Error("Invalid amount");
  const [whole, fraction = ""] = clean.split(".");
  const paise = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"));
  if (paise > BigInt(MAX_SAFE_PAISE)) throw new Error("Amount is too large");
  return Number(paise);
}

export function formatIndianNumber(value: number | null | undefined): string { if (value == null || !Number.isFinite(value)) return "\u2014"; return numberFormatter.format(value); }
export function formatINR(paise: number | null | undefined): string { if (paise == null || !Number.isFinite(paise)) return "\u2014"; return `₹${formatIndianNumber(paise / 100)}`; }
export function formatCompactINR(paise: number | null | undefined): string {
  if (paise == null || !Number.isFinite(paise)) return "\u2014";
  const value = paise / 100; const absolute = Math.abs(value);
  if (absolute < 1_000) return formatINR(paise);
  let divisor = 1_000; let unit = "K";
  if (absolute >= 100_000) { divisor = 100_000; unit = "L"; }
  if (absolute >= 10_000_000) { divisor = 10_000_000; unit = "Cr"; }
  let rounded = roundMagnitude(value / divisor);
  if (unit === "K" && Math.abs(rounded) >= 100) { rounded = roundMagnitude(value / 100_000); unit = "L"; }
  if (unit === "L" && Math.abs(rounded) >= 100) { rounded = roundMagnitude(value / 10_000_000); unit = "Cr"; }
  return `₹${rounded} ${unit}`;
}
export function formatPercentage(value: number | null | undefined): string { if (value == null || !Number.isFinite(value)) return "\u2014"; return `${new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value)}%`; }

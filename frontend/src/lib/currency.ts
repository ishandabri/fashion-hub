const numberFormatter = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function toPaise(value: string): number {
  const clean = value.replace(/,/g, "").trim();
  if (!/^\d+(\.\d{0,2})?$/.test(clean)) throw new Error("Invalid amount");
  const [whole, fraction = ""] = clean.split(".");
  return Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
}

export function formatINR(paise: number | null | undefined): string {
  if (paise == null || !Number.isFinite(paise)) return "—";
  return `₹${numberFormatter.format(paise / 100)}`;
}

export function formatCompactINR(paise: number | null | undefined): string {
  if (paise == null || !Number.isFinite(paise)) return "—";
  const value = paise / 100;
  const absolute = Math.abs(value);
  if (absolute < 1_000) return formatINR(paise);
  if (absolute < 100_000) return `₹${(value / 1_000).toFixed(2)} K`;
  if (absolute < 10_000_000) return `₹${(value / 100_000).toFixed(2)} L`;
  return `₹${(value / 10_000_000).toFixed(2)} Cr`;
}


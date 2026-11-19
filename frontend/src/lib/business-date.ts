const indiaDateFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Kolkata",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

function parts(now: Date): Record<string, string> {
  return Object.fromEntries(indiaDateFormatter.formatToParts(now).filter(part => part.type !== "literal").map(part => [part.type, part.value]));
}

export function indiaBusinessDate(now = new Date()): string {
  const value = parts(now);
  return `${value.year}-${value.month}-${value.day}`;
}

export function indiaBusinessMonth(now = new Date()): string {
  return indiaBusinessDate(now).slice(0, 7);
}

import { describe, expect, it } from "vitest";
import { formatCompactINR, formatINR, formatPercentage, toPaise } from "./currency";

describe("currency utilities", () => {
  it("converts rupee input to paise exactly", () => {
    expect(toPaise("12,500.50")).toBe(1250050);
    expect(toPaise("0")).toBe(0);
  });

  it("formats Indian currency", () => {
    expect(formatINR(1250000)).toBe("₹12,500");
    expect(formatINR(125000000)).toBe("₹12,50,000");
    expect(formatINR(null)).toBe("—");
  });

  it("uses Indian compact units", () => {
    expect(formatCompactINR(95000)).toBe("₹950");
    expect(formatCompactINR(1250000)).toBe("₹13 K");
    expect(formatCompactINR(12500000)).toBe("₹1 L");
    expect(formatCompactINR(1250000000)).toBe("₹1 Cr");
  });

  it("formats percentages", () => {
    expect(formatPercentage(64.5)).toBe("65%");
    expect(formatPercentage(null)).toBe("—");
  });
});


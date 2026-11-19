import { describe, expect, it } from "vitest";
import { formatCompactINR, formatINR, formatIndianNumber, formatPercentage, MAX_SAFE_PAISE, toPaise } from "./currency";

describe("currency utilities", () => {
  it("converts rupee input to paise exactly", () => {
    expect(toPaise("12,500.50")).toBe(1250050);
    expect(toPaise("0")).toBe(0);
    expect(() => toPaise("90071992547409.92")).toThrow("too large");
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
    expect(formatCompactINR(9995000)).toBe("₹1 L");
    expect(formatCompactINR(999500000)).toBe("₹1 Cr");
    expect(formatCompactINR(-1250000)).toBe("₹-13 K");
    expect(MAX_SAFE_PAISE).toBe(Number.MAX_SAFE_INTEGER);
  });

  it("formats Indian numbers", () => expect(formatIndianNumber(1250000)).toBe("12,50,000"));

  it("formats percentages", () => {
    expect(formatPercentage(64.5)).toBe("65%");
    expect(formatPercentage(null)).toBe("—");
  });
});


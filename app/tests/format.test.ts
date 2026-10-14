// Sayı biçimi (SPEC_APP §4).
import { describe, expect, it } from "vitest";

import { fixed1, pct0, pctSigned1, points1, pyRepr, tl2 } from "../src/render/format";

describe("biçim", () => {
  it("getiri, olasılık, fiyat, puan", () => {
    expect(pctSigned1(0.077)).toBe("+%7.7");
    expect(pctSigned1(-0.0321)).toBe("-%3.2");
    expect(pctSigned1(-0.00001)).toBe("%0.0");
    expect(pctSigned1(null)).toBe("—");
    expect(pct0(0.914)).toBe("%91");
    expect(tl2(27.4812)).toBe("27.48 TL");
    expect(points1(0.030)).toBe("3.0 puan");
    expect(points1(0.0046)).toBe("0.5 puan");
    expect(fixed1(3.2811)).toBe("3.3");
    expect(pctSigned1("NaN")).toBe("NaN");
  });

  it("Python repr ile aynı", () => {
    const cases: [number, string][] = [
      [0.1, "0.1"], [1, "1.0"], [-0.0, "-0.0"], [1e-5, "1e-05"], [0.0001, "0.0001"], [1e16, "1e+16"],
      [123456789012345.6, "123456789012345.6"], [0.08728023453804833, "0.08728023453804833"], [2.5e-7, "2.5e-07"],
      [1.5e300, "1.5e+300"], [100, "100.0"],
    ];
    for (const [x, want] of cases) expect(pyRepr(x), String(x)).toBe(want);
    expect(pyRepr("Infinity")).toBe("inf");
  });
});

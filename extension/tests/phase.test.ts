/** Popup phase tests prevent accidental success and invalid retry transitions. */

import { describe, expect, it } from "vitest";

import { transitionPhase } from "../src/ui/phase";

describe("popup state transitions", () => {
  it("permits the complete successful path", () => {
    expect(transitionPhase("loading", "review")).toBe("review");
    expect(transitionPhase("review", "working")).toBe("working");
    expect(transitionPhase("working", "success")).toBe("success");
  });

  it("permits failure from each active phase", () => {
    expect(transitionPhase("loading", "error")).toBe("error");
    expect(transitionPhase("review", "error")).toBe("error");
    expect(transitionPhase("working", "error")).toBe("error");
  });

  it("rejects skipping directly from review to success", () => {
    expect(() => transitionPhase("review", "success")).toThrow(/Cannot transition/u);
  });
});

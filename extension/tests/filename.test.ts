/** Filename tests cover the default title and Windows path constraints. */

import { describe, expect, it } from "vitest";

import { defaultTitle, sanitizePdfFileName, senderDisplayName } from "../src/services/filename";

describe("filename generation", () => {
  it("uses the sender display name in the dated default title", () => {
    const title = defaultTitle(
      new Date(2026, 7, 10, 12, 30),
      '"Erika Muster" <erika@example.test>',
      "Rechnung August",
      "E-Mail",
    );
    expect(title).toBe("2026-08-10 - Erika Muster - Rechnung August");
  });

  it("sanitizes illegal Windows characters and reserved device names", () => {
    expect(sanitizePdfFileName('Rechnung: 10/08 <final>', "E-Mail")).toBe(
      "Rechnung_ 10_08 _final_.pdf",
    );
    expect(sanitizePdfFileName("CON", "E-Mail")).toBe("_CON.pdf");
  });

  it("falls back to the address when no display name is present", () => {
    expect(senderDisplayName("erika@example.test")).toBe("erika@example.test");
  });
});

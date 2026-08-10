/** Language helpers keep locale fallback deterministic and intentionally bounded. */

import { describe, expect, it } from "vitest";

import { isUiLanguage, languageFromLocale } from "../src/services/language";

describe("UI language selection", () => {
  it("supports only the reviewed German and English catalogs", () => {
    expect(isUiLanguage("de")).toBe(true);
    expect(isUiLanguage("en")).toBe(true);
    expect(isUiLanguage("fr")).toBe(false);
  });

  it("uses German for German locales and English as the global fallback", () => {
    expect(languageFromLocale("de-DE")).toBe("de");
    expect(languageFromLocale("de-AT")).toBe("de");
    expect(languageFromLocale("en-GB")).toBe("en");
    expect(languageFromLocale("fr-FR")).toBe("en");
  });
});

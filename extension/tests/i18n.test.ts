/** Locale tests ensure German and English expose the same reviewed UI contract. */

import { readFile } from "node:fs/promises";
import path from "node:path";
import { describe, expect, it } from "vitest";

interface LocaleEntry {
  readonly message: string;
}

type Locale = Record<string, LocaleEntry>;

async function readLocale(language: string): Promise<Locale> {
  const localePath = path.resolve(import.meta.dirname, "..", "_locales", language, "messages.json");
  return JSON.parse(await readFile(localePath, "utf-8")) as Locale;
}

describe("extension locales", () => {
  it("keeps German and English message keys complete and non-empty", async () => {
    const [german, english] = await Promise.all([readLocale("de"), readLocale("en")]);
    expect(Object.keys(german).sort()).toEqual(Object.keys(english).sort());
    expect(Object.values(german).every((entry) => entry.message.trim().length > 0)).toBe(true);
    expect(Object.values(english).every((entry) => entry.message.trim().length > 0)).toBe(true);
  });

  it("resolves every localized manifest placeholder in both locales", async () => {
    const manifestPath = path.resolve(import.meta.dirname, "..", "manifest.json");
    const manifest = await readFile(manifestPath, "utf-8");
    const placeholders = [...manifest.matchAll(/__MSG_([A-Za-z0-9_]+)__/gu)].map((match) => match[1]);
    const [german, english] = await Promise.all([readLocale("de"), readLocale("en")]);

    expect(placeholders.length).toBeGreaterThan(0);
    for (const placeholder of placeholders) {
      expect(placeholder).toBeDefined();
      expect(german).toHaveProperty(placeholder ?? "");
      expect(english).toHaveProperty(placeholder ?? "");
    }
  });

  it("resolves every localized page key in both locales", async () => {
    const pagePaths = [
      path.resolve(import.meta.dirname, "..", "pages", "options", "options.html"),
      path.resolve(import.meta.dirname, "..", "pages", "popup", "popup.html"),
    ];
    const pages = await Promise.all(pagePaths.map(async (pagePath) => readFile(pagePath, "utf-8")));
    const keys = pages.flatMap((page) =>
      [...page.matchAll(/data-i18n(?:-placeholder)?="([A-Za-z0-9_]+)"/gu)].map(
        (match) => match[1],
      ),
    );
    const [german, english] = await Promise.all([readLocale("de"), readLocale("en")]);

    expect(keys.length).toBeGreaterThan(0);
    for (const key of keys) {
      expect(key).toBeDefined();
      expect(german).toHaveProperty(key ?? "");
      expect(english).toHaveProperty(key ?? "");
    }
  });
});

/** Settings tests preserve the privacy-first image default and validate persisted choices. */

import { afterEach, describe, expect, it, vi } from "vitest";

import { DEFAULT_IMAGE_MODE, isImageMode, loadSettings, saveSettings } from "../src/services/settings";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  Reflect.deleteProperty(globalThis, "browser");
});

function installStorage(stored: Record<string, unknown>): ReturnType<typeof vi.fn> {
  const set = vi.fn(() => Promise.resolve(undefined));
  Object.defineProperty(globalThis, "browser", {
    configurable: true,
    value: {
      i18n: {
        getUILanguage: () => "en-US",
      },
      runtime: {
        getManifest: () => ({ version: "1.1.0" }),
        getURL: (path: string) => `moz-extension://test/${path}`,
      },
      storage: {
        local: {
          get: vi.fn(() => Promise.resolve(stored)),
          set,
        },
      },
    },
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve(
        new Response(JSON.stringify({ language: "auto", version: "1.1.0" }), { status: 200 }),
      ),
    ),
  );
  return set;
}

describe("extension settings", () => {
  it("defaults unknown image preferences to placeholders", async () => {
    installStorage({ imageMode: "unexpected", outputDirectory: "D:\\Archive" });

    await expect(loadSettings()).resolves.toEqual({
      imageMode: DEFAULT_IMAGE_MODE,
      outputDirectory: "D:\\Archive",
      separatorPages: false,
      uiLanguage: "en",
    });
    expect(isImageMode("embed")).toBe(true);
    expect(isImageMode("unexpected")).toBe(false);
  });

  it("saves the selected image mode and a trimmed directory", async () => {
    const set = installStorage({});

    await saveSettings({
      imageMode: "embed",
      outputDirectory: "  D:\\Archive  ",
      separatorPages: true,
      uiLanguage: "de",
    });

    expect(set).toHaveBeenLastCalledWith({
      imageMode: "embed",
      outputDirectory: "D:\\Archive",
      separatorPages: true,
    });
  });
});

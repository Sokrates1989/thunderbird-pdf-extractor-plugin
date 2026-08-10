/** Non-secret extension preferences stored in Thunderbird storage.local. */

import type { ExtensionSettings, ImageMode, UiLanguage } from "../domain/models";
import { initializeLanguage, isUiLanguage, setUiLanguage } from "./language";

const OUTPUT_DIRECTORY_KEY = "outputDirectory";
const IMAGE_MODE_KEY = "imageMode";
const SEPARATOR_PAGES_KEY = "separatorPages";

export const DEFAULT_IMAGE_MODE: ImageMode = "placeholder";

/** Validate a persisted or UI-provided value before it crosses the archive boundary. */
export function isImageMode(value: unknown): value is ImageMode {
  return value === "placeholder" || value === "embed";
}

export async function loadSettings(): Promise<ExtensionSettings> {
  const stored = await browser.storage.local.get([
    OUTPUT_DIRECTORY_KEY,
    IMAGE_MODE_KEY,
    SEPARATOR_PAGES_KEY,
  ]);
  const outputDirectory = stored[OUTPUT_DIRECTORY_KEY];
  const imageMode = stored[IMAGE_MODE_KEY];
  return {
    imageMode: isImageMode(imageMode) ? imageMode : DEFAULT_IMAGE_MODE,
    outputDirectory: typeof outputDirectory === "string" ? outputDirectory : "",
    separatorPages: stored[SEPARATOR_PAGES_KEY] === true,
    uiLanguage: await initializeLanguage(),
  };
}

export async function saveSettings(settings: ExtensionSettings): Promise<void> {
  await setUiLanguage(settings.uiLanguage);
  await browser.storage.local.set({
    [IMAGE_MODE_KEY]: settings.imageMode,
    [OUTPUT_DIRECTORY_KEY]: settings.outputDirectory.trim(),
    [SEPARATOR_PAGES_KEY]: settings.separatorPages,
  });
}

export { isUiLanguage };
export type { UiLanguage };

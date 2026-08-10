/** Persisted UI-language selection with optional Windows-installer defaults. */

import type { UiLanguage } from "../domain/models";

const UI_LANGUAGE_KEY = "uiLanguage";
const INSTALLER_LANGUAGE_VERSION_KEY = "installerLanguageVersion";
const INSTALL_DEFAULTS_PATH = "install-defaults.json";

interface InstallDefaults {
  readonly language?: unknown;
  readonly version?: unknown;
}

let activeLanguage: UiLanguage | undefined;

export function isUiLanguage(value: unknown): value is UiLanguage {
  return value === "de" || value === "en";
}

export function languageFromLocale(locale: string): UiLanguage {
  return locale.toLowerCase().startsWith("de") ? "de" : "en";
}

async function loadInstallDefaults(): Promise<InstallDefaults> {
  try {
    const response = await fetch(browser.runtime.getURL(INSTALL_DEFAULTS_PATH));
    if (!response.ok) {
      return {};
    }
    return (await response.json()) as InstallDefaults;
  } catch {
    return {};
  }
}

function extensionVersion(): string {
  return browser.runtime.getManifest().version;
}

export async function initializeLanguage(force = false): Promise<UiLanguage> {
  if (!force && activeLanguage !== undefined) {
    return activeLanguage;
  }

  const version = extensionVersion();
  const [stored, installDefaults] = await Promise.all([
    browser.storage.local.get([UI_LANGUAGE_KEY, INSTALLER_LANGUAGE_VERSION_KEY]),
    loadInstallDefaults(),
  ]);
  const storedLanguage = stored[UI_LANGUAGE_KEY];
  const installerVersion = stored[INSTALLER_LANGUAGE_VERSION_KEY];
  const installerLanguage = installDefaults.language;
  const installerDefaultApplies =
    isUiLanguage(installerLanguage) &&
    installDefaults.version === version &&
    installerVersion !== version;

  activeLanguage = installerDefaultApplies
    ? installerLanguage
    : isUiLanguage(storedLanguage)
      ? storedLanguage
      : languageFromLocale(browser.i18n.getUILanguage());

  await browser.storage.local.set({
    [INSTALLER_LANGUAGE_VERSION_KEY]: version,
    [UI_LANGUAGE_KEY]: activeLanguage,
  });
  return activeLanguage;
}

export function currentLanguage(): UiLanguage {
  return activeLanguage ?? "en";
}

export async function setUiLanguage(language: UiLanguage): Promise<void> {
  activeLanguage = language;
  await browser.storage.local.set({
    [INSTALLER_LANGUAGE_VERSION_KEY]: extensionVersion(),
    [UI_LANGUAGE_KEY]: language,
  });
}

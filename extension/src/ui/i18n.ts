/** Safe catalog-backed localization helpers for extension-owned pages. */

import { UserFacingError } from "../domain/errors";
import type { UiLanguage } from "../domain/models";
import { currentLanguage, initializeLanguage } from "../services/language";

interface LocaleEntry {
  readonly message: string;
}

type LocaleCatalog = Readonly<Record<string, LocaleEntry>>;

let catalog: LocaleCatalog = {};
let fallbackCatalog: LocaleCatalog = {};

async function loadCatalog(language: UiLanguage): Promise<LocaleCatalog> {
  const response = await fetch(browser.runtime.getURL(`_locales/${language}/messages.json`));
  if (!response.ok) {
    throw new Error(`Locale catalog '${language}' could not be loaded.`);
  }
  return (await response.json()) as LocaleCatalog;
}

export async function initializeLocalization(force = false): Promise<UiLanguage> {
  const language = await initializeLanguage(force);
  [catalog, fallbackCatalog] = await Promise.all([
    loadCatalog(language),
    language === "en" ? Promise.resolve({}) : loadCatalog("en"),
  ]);
  return language;
}

function substitutionValues(substitutions?: string | readonly string[]): readonly string[] {
  if (substitutions === undefined) {
    return [];
  }
  return typeof substitutions === "string" ? [substitutions] : substitutions;
}

export function message(key: string, substitutions?: string | readonly string[]): string {
  const template = catalog[key]?.message ?? fallbackCatalog[key]?.message ?? key;
  const values = substitutionValues(substitutions);
  return template.replace(/\$(\d+)/gu, (placeholder, indexText: string) => {
    const index = Number(indexText) - 1;
    return values[index] ?? placeholder;
  });
}

export function locale(): UiLanguage {
  return currentLanguage();
}

export function localizeDocument(): void {
  document.documentElement.lang = locale();
  for (const element of document.querySelectorAll<HTMLElement>("[data-i18n]")) {
    const key = element.dataset.i18n;
    if (key !== undefined) {
      element.textContent = message(key);
    }
  }
  for (const element of document.querySelectorAll<HTMLElement>("[data-i18n-aria-label]")) {
    const key = element.dataset.i18nAriaLabel;
    if (key !== undefined) {
      element.setAttribute("aria-label", message(key));
    }
  }
  for (const element of document.querySelectorAll<HTMLInputElement>("[data-i18n-placeholder]")) {
    const key = element.dataset.i18nPlaceholder;
    if (key !== undefined) {
      element.placeholder = message(key);
    }
  }
}

/** Translate stable failure codes at the presentation boundary without exposing host prose. */
export function localizedErrorMessage(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return message("archiveCancelled");
  }
  if (error instanceof UserFacingError) {
    const keyByCode: Readonly<Record<string, string>> = {
      host_disconnected: "errorHostDisconnected",
      host_timeout: "errorHostTimeout",
      incompatible_host: "errorIncompatibleHost",
      output_directory_missing: "directoryNotConfigured",
      single_message_required: "singleMessageRequired",
    };
    const key = keyByCode[error.code];
    return key === undefined ? message("technicalErrorWithCode", error.code) : message(key);
  }
  return message("technicalErrorGeneric");
}

type ElementConstructor<T> = new () => T;

export function requiredElement<T extends HTMLElement>(id: string, type: ElementConstructor<T>): T {
  const element = document.getElementById(id);
  if (!(element instanceof type)) {
    throw new Error(`Required element #${id} is missing or has the wrong type.`);
  }
  return element;
}

/** Safe DOM localization helpers for static extension pages. */

export function message(key: string, substitutions?: string | readonly string[]): string {
  return browser.i18n.getMessage(key, substitutions);
}

export function localizeDocument(): void {
  document.documentElement.lang = navigator.language.split("-")[0] ?? "en";
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

type ElementConstructor<T> = new () => T;

export function requiredElement<T extends HTMLElement>(id: string, type: ElementConstructor<T>): T {
  const element = document.getElementById(id);
  if (!(element instanceof type)) {
    throw new Error(`Required element #${id} is missing or has the wrong type.`);
  }
  return element;
}

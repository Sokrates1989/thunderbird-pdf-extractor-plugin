/** Non-persistent background entry point for menu and trusted integration actions. */

import { handleExternalIntegrationRequest } from "./integration/external";
import { initializeLocalization, message } from "./ui/i18n";

const MENU_ID = "archive-message-as-pdf";

function reportBackgroundError(error: unknown): void {
  const detail = error instanceof Error ? error.message : String(error);
  console.error(`PDF Archiver for Thunderbird background error: ${detail}`);
}

async function installMenu(): Promise<void> {
  try {
    await browser.menus.remove(MENU_ID);
  } catch {
    // A missing menu is the expected state on first installation.
  }
  await browser.menus.create({
    contexts: ["message_list", "page"],
    id: MENU_ID,
    title: message("actionTitle"),
  });
}

async function initializeMenu(): Promise<void> {
  await initializeLocalization(true);
  await installMenu();
}

/** Open the existing single-message review workflow for an explicit message ID. */
async function openReviewWindow(messageId: number): Promise<void> {
  const parameters = new URLSearchParams({ messageId: String(messageId) });
  await browser.windows.create({
    height: 680,
    type: "popup",
    url: browser.runtime.getURL(`pages/popup/popup.html?${parameters.toString()}`),
    width: 520,
  });
}

browser.runtime.onInstalled.addListener(() => {
  void initializeMenu().catch(reportBackgroundError);
});

browser.runtime.onMessage.addListener((request) => {
  if (
    typeof request === "object" &&
    request !== null &&
    "type" in request &&
    request.type === "refresh-language"
  ) {
    return initializeMenu().catch(reportBackgroundError);
  }
  return undefined;
});

browser.runtime.onMessageExternal.addListener((request, sender) =>
  handleExternalIntegrationRequest(request, sender, openReviewWindow),
);

browser.menus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== MENU_ID) {
    return;
  }
  const selected = info.selectedMessages?.messages ?? [];
  const parameters = new URLSearchParams();
  if (selected.length === 1 && selected[0] !== undefined) {
    void openReviewWindow(selected[0].id).catch(reportBackgroundError);
    return;
  } else if (selected.length > 1) {
    parameters.set("selectionCount", String(selected.length));
  } else if (tab.id !== undefined) {
    parameters.set("tabId", String(tab.id));
  }
  const suffix = parameters.size > 0 ? `?${parameters.toString()}` : "";
  void browser.windows
    .create({
      height: 680,
      type: "popup",
      url: browser.runtime.getURL(`pages/popup/popup.html${suffix}`),
      width: 520,
    })
    .catch(reportBackgroundError);
});

void initializeMenu().catch(reportBackgroundError);

/** Non-persistent background entry point for the Thunderbird action menu. */

const MENU_ID = "archive-message-as-pdf";

function reportBackgroundError(error: unknown): void {
  const detail = error instanceof Error ? error.message : String(error);
  console.error(`Thunderbird PDF Archiver background error: ${detail}`);
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
    title: browser.i18n.getMessage("actionTitle"),
  });
}

browser.runtime.onInstalled.addListener(() => {
  void installMenu().catch(reportBackgroundError);
});

browser.menus.onClicked.addListener((info, tab) => {
  if (info.menuItemId !== MENU_ID) {
    return;
  }
  const selected = info.selectedMessages?.messages ?? [];
  const parameters = new URLSearchParams();
  if (selected.length === 1 && selected[0] !== undefined) {
    parameters.set("messageId", String(selected[0].id));
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

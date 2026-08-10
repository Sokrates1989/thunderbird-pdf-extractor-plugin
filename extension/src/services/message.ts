/** Thunderbird message selection and metadata adaptation. */

import { UserFacingError } from "../domain/errors";
import type { AttachmentSummary, MessageSummary } from "../domain/models";

export function requireSingleMessage(
  messages: readonly ThunderbirdMessageHeader[],
): ThunderbirdMessageHeader {
  if (messages.length !== 1) {
    throw new UserFacingError(
      "single_message_required",
      `Expected one message, received ${String(messages.length)}.`,
    );
  }
  const message = messages[0];
  if (message === undefined) {
    throw new UserFacingError("single_message_required", "No message is available.");
  }
  return message;
}

export async function displayedMessage(
  explicitMessageId?: number,
  sourceTabId?: number,
): Promise<MessageSummary> {
  let header: ThunderbirdMessageHeader;
  if (explicitMessageId === undefined) {
    let tabId = sourceTabId;
    if (tabId === undefined) {
      const activeTabs = await browser.tabs.query({ active: true, currentWindow: true });
      tabId = activeTabs[0]?.id;
    }
    if (tabId === undefined) {
      throw new UserFacingError(
        "no_active_tab",
        "No active Thunderbird message tab is available.",
      );
    }
    const displayed = await browser.messageDisplay.getDisplayedMessages(tabId);
    header = requireSingleMessage(displayed.messages);
  } else {
    header = await browser.messages.get(explicitMessageId);
  }

  return {
    author: header.author,
    cc: header.ccList ?? [],
    date: header.date,
    headerMessageId: header.headerMessageId ?? "",
    id: header.id,
    recipients: header.recipients ?? [],
    subject: header.subject,
  };
}

export async function listAttachmentSummaries(messageId: number): Promise<readonly AttachmentSummary[]> {
  const attachments = await browser.messages.listAttachments(messageId);
  return summarizeAttachments(attachments);
}

export function summarizeAttachments(
  attachments: readonly ThunderbirdAttachment[],
): readonly AttachmentSummary[] {
  /** Assign real-attachment ordinals while keeping inline images visible but unselectable. */
  let archiveIndex = 0;
  return attachments.map((attachment, index) => {
    const classification =
      attachment.contentDisposition === "inline" ||
      (attachment.contentDisposition !== "attachment" &&
        typeof attachment.contentId === "string" &&
        attachment.contentId.length > 0 &&
        attachment.contentType.startsWith("image/"))
        ? "inline"
        : "attachment";
    const currentArchiveIndex = classification === "attachment" ? archiveIndex++ : null;
    return {
      archiveIndex: currentArchiveIndex,
      classification,
      contentType: attachment.contentType,
      index,
      name: attachment.name,
      size: attachment.size,
    };
  });
}

export async function rawMessage(messageId: number): Promise<File> {
  return browser.messages.getRaw(messageId, { data_format: "File", decrypt: true });
}

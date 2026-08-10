/** Review popup for a single explicit email-to-PDF operation. */

import { UserFacingError, errorMessage } from "../domain/errors";
import type { AttachmentSummary, ImageMode, MessageSummary } from "../domain/models";
import { NativeArchiveClient, type ProgressUpdate } from "../protocol/native-client";
import { attachmentSupport, type AttachmentSupportReason } from "../services/attachment-support";
import { defaultTitle, sanitizePdfFileName } from "../services/filename";
import { displayedMessage, listAttachmentSummaries, rawMessage } from "../services/message";
import { DEFAULT_IMAGE_MODE, isImageMode, loadSettings, saveSettings } from "../services/settings";
import { createTransferPayload } from "../services/transfer";
import { localizeDocument, message, requiredElement } from "./i18n";
import { transitionPhase, type PopupPhase } from "./phase";

const loadingPanel = requiredElement("loading-panel", HTMLElement);
const reviewPanel = requiredElement("review-panel", HTMLElement);
const progressPanel = requiredElement("progress-panel", HTMLElement);
const resultPanel = requiredElement("result-panel", HTMLElement);
const senderValue = requiredElement("sender-value", HTMLElement);
const subjectValue = requiredElement("subject-value", HTMLElement);
const dateValue = requiredElement("date-value", HTMLElement);
const titleInput = requiredElement("title-input", HTMLInputElement);
const fileNameValue = requiredElement("filename-value", HTMLOutputElement);
const directoryValue = requiredElement("directory-value", HTMLOutputElement);
const includeBody = requiredElement("include-body", HTMLInputElement);
const imageModeSelect = requiredElement("image-mode", HTMLSelectElement);
const separatorPages = requiredElement("separator-pages", HTMLInputElement);
const attachmentList = requiredElement("attachment-list", HTMLUListElement);
const reviewStatus = requiredElement("review-status", HTMLElement);
const progressLabel = requiredElement("progress-label", HTMLElement);
const progressBar = requiredElement("progress-bar", HTMLProgressElement);
const resultHeading = requiredElement("result-heading", HTMLElement);
const resultSummary = requiredElement("result-summary", HTMLElement);
const resultPath = requiredElement("result-path", HTMLElement);
const resultAttachments = requiredElement("result-attachments", HTMLElement);
const errorDetails = requiredElement("error-details", HTMLDetailsElement);
const errorDetailText = requiredElement("error-detail-text", HTMLElement);
const archiveButton = requiredElement("archive-button", HTMLButtonElement);
const cancelButton = requiredElement("cancel-button", HTMLButtonElement);
const openOptionsButton = requiredElement("open-options", HTMLButtonElement);
const selectDirectoryButton = requiredElement("select-directory", HTMLButtonElement);
const openDirectoryButton = requiredElement("open-directory", HTMLButtonElement);

let selectedMessage: MessageSummary | undefined;
let detectedAttachments: readonly AttachmentSummary[] = [];
let outputDirectory = "";
let imageMode: ImageMode = DEFAULT_IMAGE_MODE;
let libreOfficeAvailable = false;
const selectedAttachmentIndices = new Set<number>();
let currentAbortController: AbortController | undefined;
let currentPhase: PopupPhase = "loading";

function showPanel(panel: HTMLElement, nextPhase: PopupPhase): void {
  currentPhase = transitionPhase(currentPhase, nextPhase);
  for (const candidate of [loadingPanel, reviewPanel, progressPanel, resultPanel]) {
    candidate.classList.toggle("hidden", candidate !== panel);
  }
}

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${String(size)} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KiB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MiB`;
}

function renderAttachments(attachments: readonly AttachmentSummary[]): void {
  attachmentList.replaceChildren();
  if (attachments.length === 0) {
    const item = document.createElement("li");
    item.textContent = message("noAttachments");
    attachmentList.append(item);
    return;
  }

  for (const attachment of attachments) {
    const support = attachmentSupport(attachment, libreOfficeAvailable);
    const item = document.createElement("li");
    item.className = "attachment-item";
    const main = document.createElement("div");
    main.className = "attachment-main";
    const name = document.createElement("span");
    name.className = "attachment-name";
    name.textContent = attachment.name;
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.disabled = !support.supported || attachment.archiveIndex === null;
    checkbox.checked =
      attachment.archiveIndex !== null && selectedAttachmentIndices.has(attachment.archiveIndex);
    checkbox.setAttribute("aria-label", attachment.name);
    checkbox.addEventListener("change", () => {
      if (attachment.archiveIndex === null) {
        return;
      }
      if (checkbox.checked) {
        selectedAttachmentIndices.add(attachment.archiveIndex);
      } else {
        selectedAttachmentIndices.delete(attachment.archiveIndex);
      }
    });
    main.append(name, checkbox);
    const detail = document.createElement("div");
    detail.className = "attachment-detail";
    detail.textContent = message("attachmentDetail", [attachment.contentType, formatBytes(attachment.size)]);
    const status = document.createElement("div");
    status.className = "attachment-status";
    const statusKeyByReason: Readonly<Record<AttachmentSupportReason, string>> = {
      inline: "inlineImageExcluded",
      libreoffice_required: "attachmentLibreOfficeRequired",
      supported: "attachmentIncludedDefault",
      unsupported: "attachmentUnsupported",
    };
    status.textContent = message(statusKeyByReason[support.reason]);
    item.append(main, detail, status);
    attachmentList.append(item);
  }
}

function refreshFilename(): void {
  fileNameValue.textContent = sanitizePdfFileName(titleInput.value);
}

function progressMessage(progress: ProgressUpdate): string {
  const keyByStage: Readonly<Record<string, string>> = {
    parsing: "progressParsing",
    reading: "progressReading",
    rendering: "progressRendering",
    saving: "progressSaving",
    transferring: "progressTransferring",
    converting: "progressConverting",
    merging: "progressMerging",
  };
  const base = message(keyByStage[progress.stage] ?? "progressGeneric");
  return progress.detail.length > 0 ? `${base} ${progress.detail}` : base;
}

function updateProgress(progress: ProgressUpdate): void {
  progressLabel.textContent = progressMessage(progress);
  progressBar.max = Math.max(progress.total, 1);
  progressBar.value = Math.min(progress.completed, progressBar.max);
}

function userSummary(error: unknown): string {
  if (error instanceof DOMException && error.name === "AbortError") {
    return message("archiveCancelled");
  }
  if (error instanceof UserFacingError && error.code === "single_message_required") {
    return message("singleMessageRequired");
  }
  return message("archiveErrorSummary");
}

function showError(error: unknown): void {
  showPanel(resultPanel, "error");
  resultHeading.textContent = message("archiveErrorHeading");
  resultSummary.textContent = userSummary(error);
  resultPath.textContent = "";
  resultAttachments.replaceChildren();
  errorDetailText.textContent = errorMessage(error);
  errorDetails.classList.remove("hidden");
  archiveButton.disabled = true;
  archiveButton.classList.remove("hidden");
  openDirectoryButton.classList.add("hidden");
  cancelButton.textContent = message("closeButton");
  currentAbortController = undefined;
}

async function loadReview(): Promise<void> {
  localizeDocument();
  showPanel(loadingPanel, "loading");
  const parameters = new URLSearchParams(window.location.search);
  const selectionCount = Number(parameters.get("selectionCount") ?? "0");
  if (selectionCount > 1) {
    throw new UserFacingError(
      "single_message_required",
      `Received a selection of ${String(selectionCount)} messages.`,
    );
  }
  const messageIdParameter = parameters.get("messageId");
  const explicitMessageId = messageIdParameter === null ? undefined : Number(messageIdParameter);
  if (explicitMessageId !== undefined && !Number.isSafeInteger(explicitMessageId)) {
    throw new UserFacingError("invalid_message_id", "The selected message ID is invalid.");
  }
  const tabIdParameter = parameters.get("tabId");
  const sourceTabId = tabIdParameter === null ? undefined : Number(tabIdParameter);
  if (sourceTabId !== undefined && !Number.isSafeInteger(sourceTabId)) {
    throw new UserFacingError("invalid_tab_id", "The source tab ID is invalid.");
  }

  const [summary, settings] = await Promise.all([
    displayedMessage(explicitMessageId, sourceTabId),
    loadSettings(),
  ]);
  const [attachments, capabilities] = await Promise.all([
    listAttachmentSummaries(summary.id),
    new NativeArchiveClient().capabilities(),
  ]);
  selectedMessage = summary;
  detectedAttachments = attachments;
  outputDirectory = settings.outputDirectory;
  imageMode = settings.imageMode;
  libreOfficeAvailable = capabilities.libreOfficeAvailable;
  separatorPages.checked = settings.separatorPages;
  selectedAttachmentIndices.clear();
  for (const attachment of attachments) {
    if (
      attachment.archiveIndex !== null &&
      attachmentSupport(attachment, libreOfficeAvailable).supported
    ) {
      selectedAttachmentIndices.add(attachment.archiveIndex);
    }
  }

  senderValue.textContent = summary.author;
  subjectValue.textContent = summary.subject;
  dateValue.textContent = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(summary.date);
  titleInput.value = defaultTitle(summary.date, summary.author, summary.subject);
  directoryValue.textContent = outputDirectory.length > 0 ? outputDirectory : message("directoryNotConfigured");
  imageModeSelect.value = imageMode;
  renderAttachments(attachments);
  refreshFilename();
  archiveButton.disabled = outputDirectory.length === 0;
  showPanel(reviewPanel, "review");
}

/** Select and persist a target folder while leaving cancellation as a no-op. */
async function browseForDirectory(): Promise<void> {
  selectDirectoryButton.disabled = true;
  reviewStatus.textContent = message("folderPickerOpening");
  try {
    const selected = await new NativeArchiveClient().selectDirectory(
      outputDirectory,
      message("folderPickerTitle"),
    );
    if (selected === undefined) {
      reviewStatus.textContent = "";
      return;
    }
    outputDirectory = selected;
    directoryValue.textContent = selected;
    archiveButton.disabled = false;
    reviewStatus.textContent = message("folderSelected");
    await saveSettings({
      imageMode,
      outputDirectory,
      separatorPages: separatorPages.checked,
    });
  } catch (error: unknown) {
    reviewStatus.textContent = message("connectionFailure", errorMessage(error));
  } finally {
    selectDirectoryButton.disabled = false;
  }
}

async function archive(): Promise<void> {
  const messageSummary = selectedMessage;
  if (messageSummary === undefined) {
    throw new UserFacingError("no_message", "No message has been loaded.");
  }
  if (outputDirectory.length === 0) {
    throw new UserFacingError("output_directory_missing", "No output directory is configured.");
  }
  if (!isImageMode(imageModeSelect.value)) {
    throw new UserFacingError("invalid_image_mode", "The selected image mode is invalid.");
  }
  imageMode = imageModeSelect.value;
  await saveSettings({
    imageMode,
    outputDirectory,
    separatorPages: separatorPages.checked,
  });

  archiveButton.disabled = true;
  currentAbortController = new AbortController();
  showPanel(progressPanel, "working");
  updateProgress({ completed: 0, detail: "", stage: "reading", total: 1 });
  const raw = await rawMessage(messageSummary.id);
  const transfer = await createTransferPayload(raw);
  const client = new NativeArchiveClient();
  const result = await client.archive(
    transfer,
    {
      attachmentCount: detectedAttachments.filter(
        (attachment) => attachment.classification === "attachment",
      ).length,
      fileName: sanitizePdfFileName(titleInput.value),
      includeBody: includeBody.checked,
      imageMode,
      selectedAttachmentIndices: [...selectedAttachmentIndices].sort((left, right) => left - right),
      separatorPages: separatorPages.checked,
      title: titleInput.value.trim(),
    },
    outputDirectory,
    currentAbortController.signal,
    updateProgress,
  );

  showPanel(resultPanel, "success");
  resultHeading.textContent = message("archiveSuccessHeading");
  resultSummary.textContent = message("archiveSuccessSummary", [
    String(result.pageCount),
    String(result.includedAttachments.length),
    String(result.skippedAttachments.length),
  ]);
  resultPath.textContent = result.outputPath;
  resultAttachments.replaceChildren();
  for (const [labelKey, names] of [
    ["includedAttachmentsResult", result.includedAttachments],
    ["skippedAttachmentsResult", result.skippedAttachments],
  ] as const) {
    if (names.length === 0) {
      continue;
    }
    const heading = document.createElement("strong");
    heading.textContent = message(labelKey);
    const list = document.createElement("ul");
    for (const name of names) {
      const item = document.createElement("li");
      item.textContent = name;
      list.append(item);
    }
    resultAttachments.append(heading, list);
  }
  errorDetails.classList.add("hidden");
  cancelButton.textContent = message("closeButton");
  archiveButton.classList.add("hidden");
  openDirectoryButton.classList.remove("hidden");
  currentAbortController = undefined;
}

/** Open the saved PDF's destination without replacing a successful archive result on failure. */
async function openDestinationDirectory(): Promise<void> {
  openDirectoryButton.disabled = true;
  try {
    await new NativeArchiveClient().openOutputDirectory(outputDirectory);
  } catch (error: unknown) {
    errorDetailText.textContent = errorMessage(error);
    errorDetails.classList.remove("hidden");
  } finally {
    openDirectoryButton.disabled = false;
  }
}

titleInput.addEventListener("input", refreshFilename);
archiveButton.addEventListener("click", () => {
  void archive().catch(showError);
});
cancelButton.addEventListener("click", () => {
  if (currentAbortController !== undefined) {
    currentAbortController.abort();
  } else {
    window.close();
  }
});
openOptionsButton.addEventListener("click", () => {
  void browser.runtime.openOptionsPage().catch(showError);
});
selectDirectoryButton.addEventListener("click", () => {
  void browseForDirectory();
});
openDirectoryButton.addEventListener("click", () => {
  void openDestinationDirectory();
});
imageModeSelect.addEventListener("change", () => {
  if (isImageMode(imageModeSelect.value)) {
    imageMode = imageModeSelect.value;
  }
});

void loadReview().catch((error: unknown) => {
  showError(error);
});

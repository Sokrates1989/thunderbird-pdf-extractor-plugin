/** Settings page for the non-secret local output preference and host diagnostics. */

import { errorMessage } from "../domain/errors";
import { NativeArchiveClient, type NativeDiagnostics } from "../protocol/native-client";
import { isImageMode, loadSettings, saveSettings } from "../services/settings";
import { localizeDocument, message, requiredElement } from "./i18n";

const outputDirectoryInput = requiredElement("output-directory", HTMLInputElement);
const imageModeSelect = requiredElement("image-mode", HTMLSelectElement);
const separatorPagesInput = requiredElement("separator-pages", HTMLInputElement);
const browseButton = requiredElement("browse-button", HTMLButtonElement);
const testButton = requiredElement("test-button", HTMLButtonElement);
const saveButton = requiredElement("save-button", HTMLButtonElement);
const status = requiredElement("status", HTMLElement);
const diagnosticsOutput = requiredElement("diagnostics-output", HTMLPreElement);

function directoryValue(): string {
  return outputDirectoryInput.value.trim();
}

async function initialize(): Promise<void> {
  localizeDocument();
  const settings = await loadSettings();
  outputDirectoryInput.value = settings.outputDirectory;
  imageModeSelect.value = settings.imageMode;
  separatorPagesInput.checked = settings.separatorPages;
}

async function save(): Promise<void> {
  const imageMode = imageModeSelect.value;
  if (!isImageMode(imageMode)) {
    throw new Error("The selected image mode is invalid.");
  }
  await saveSettings({
    imageMode,
    outputDirectory: directoryValue(),
    separatorPages: separatorPagesInput.checked,
  });
  status.textContent = message("settingsSaved");
}

/** Let the native companion choose a local directory without filesystem permission here. */
async function browseForDirectory(): Promise<void> {
  browseButton.disabled = true;
  status.textContent = message("folderPickerOpening");
  try {
    const selected = await new NativeArchiveClient().selectDirectory(
      directoryValue(),
      message("folderPickerTitle"),
    );
    if (selected !== undefined) {
      outputDirectoryInput.value = selected;
      status.textContent = message("folderSelected");
    } else {
      status.textContent = "";
    }
  } catch (error: unknown) {
    status.textContent = message("connectionFailure", errorMessage(error));
  } finally {
    browseButton.disabled = false;
  }
}

async function testConnection(): Promise<void> {
  const outputDirectory = directoryValue();
  testButton.disabled = true;
  status.textContent = message("connectionTesting");
  diagnosticsOutput.classList.add("hidden");
  try {
    const diagnostics = await new NativeArchiveClient().diagnostics(outputDirectory);
    renderDiagnostics(diagnostics);
    status.textContent = message("diagnosticsCompleted");
  } catch (error: unknown) {
    status.textContent = message("connectionFailure", errorMessage(error));
  } finally {
    testButton.disabled = false;
  }
}

/** Present only bounded readiness values that are safe to copy into a support request. */
function renderDiagnostics(diagnostics: NativeDiagnostics): void {
  const yesNo = (value: boolean): string => message(value ? "diagnosticYes" : "diagnosticNo");
  const outputStatusKey = {
    not_configured: "diagnosticOutputNotConfigured",
    not_writable: "diagnosticOutputNotWritable",
    writable: "diagnosticOutputWritable",
  }[diagnostics.outputDirectoryStatus];
  diagnosticsOutput.textContent = [
    message("diagnosticExtensionVersion", diagnostics.extensionVersion),
    message("diagnosticHostVersion", diagnostics.hostVersion),
    message("diagnosticProtocolVersion", diagnostics.protocolVersion),
    message("diagnosticWindows", yesNo(diagnostics.platform === "windows")),
    message("diagnosticPackaged", yesNo(diagnostics.packaged)),
    message("diagnosticChromium", yesNo(diagnostics.chromiumAvailable)),
    message("diagnosticLibreOffice", yesNo(diagnostics.libreOfficeAvailable)),
    message("diagnosticAuditLog", yesNo(diagnostics.auditLogAvailable)),
    message("diagnosticOutput", message(outputStatusKey)),
  ].join("\n");
  diagnosticsOutput.classList.remove("hidden");
}

saveButton.addEventListener("click", () => {
  void save().catch((error: unknown) => {
    status.textContent = message("connectionFailure", errorMessage(error));
  });
});
testButton.addEventListener("click", () => {
  void testConnection();
});
browseButton.addEventListener("click", () => {
  void browseForDirectory();
});

void initialize().catch((error: unknown) => {
  status.textContent = message("connectionFailure", errorMessage(error));
});

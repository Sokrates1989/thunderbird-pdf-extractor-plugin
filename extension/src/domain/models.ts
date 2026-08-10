/** Shared domain models for the extension UI and native-host boundary. */

export interface MessageSummary {
  readonly author: string;
  readonly cc: readonly string[];
  readonly date: Date;
  readonly headerMessageId: string;
  readonly id: number;
  readonly recipients: readonly string[];
  readonly subject: string;
}

export interface AttachmentSummary {
  readonly archiveIndex: number | null;
  readonly classification: "attachment" | "inline";
  readonly contentType: string;
  readonly index: number;
  readonly name: string;
  readonly size: number;
}

/** Select whether body images remain placeholders or are resolved into the PDF. */
export type ImageMode = "placeholder" | "embed";

/** Explicit language used by extension-owned user interfaces. */
export type UiLanguage = "de" | "en";

export interface ExtensionSettings {
  readonly imageMode: ImageMode;
  readonly outputDirectory: string;
  readonly separatorPages: boolean;
  readonly uiLanguage: UiLanguage;
}

export interface ArchiveMetadata {
  readonly attachmentCount: number;
  readonly fileName: string;
  readonly includeBody: boolean;
  readonly imageMode: ImageMode;
  readonly selectedAttachmentIndices: readonly number[];
  readonly separatorPages: boolean;
  readonly title: string;
}

/** Review-time mirror of the native host's bounded Slice 2 converter registry. */

import type { AttachmentSummary } from "../domain/models";

export type AttachmentKind = "eml" | "html" | "image" | "office" | "pdf" | "text" | "unsupported";
export type AttachmentSupportReason = "inline" | "libreoffice_required" | "supported" | "unsupported";

export interface AttachmentSupport {
  readonly kind: AttachmentKind;
  readonly reason: AttachmentSupportReason;
  readonly supported: boolean;
}

const IMAGE_EXTENSIONS = new Set(["bmp", "jpeg", "jpg", "png", "tif", "tiff", "webp"]);
const IMAGE_MIME_TYPES = new Set([
  "image/bmp",
  "image/jpeg",
  "image/png",
  "image/tiff",
  "image/webp",
  "image/x-ms-bmp",
]);
const TEXT_EXTENSIONS = new Set(["csv", "txt"]);
const TEXT_MIME_TYPES = new Set(["application/csv", "text/csv", "text/plain"]);
const HTML_EXTENSIONS = new Set(["htm", "html"]);
const HTML_MIME_TYPES = new Set(["application/xhtml+xml", "text/html"]);
const OFFICE_EXTENSIONS = new Set(["docx", "odp", "ods", "odt", "pptx", "xlsx"]);

function fileExtension(name: string): string {
  const index = name.lastIndexOf(".");
  return index < 0 ? "" : name.slice(index + 1).toLowerCase();
}

export function attachmentKind(name: string, contentType: string): AttachmentKind {
  const extension = fileExtension(name);
  const mime = contentType.toLowerCase().split(";", 1)[0]?.trim() ?? "";
  if (mime === "application/pdf" || extension === "pdf") {
    return "pdf";
  }
  if (IMAGE_MIME_TYPES.has(mime) || IMAGE_EXTENSIONS.has(extension)) {
    return "image";
  }
  if (TEXT_MIME_TYPES.has(mime) || TEXT_EXTENSIONS.has(extension)) {
    return "text";
  }
  if (HTML_MIME_TYPES.has(mime) || HTML_EXTENSIONS.has(extension)) {
    return "html";
  }
  if (mime === "message/rfc822" || extension === "eml") {
    return "eml";
  }
  if (OFFICE_EXTENSIONS.has(extension)) {
    return "office";
  }
  return "unsupported";
}

export function attachmentSupport(
  attachment: AttachmentSummary,
  libreOfficeAvailable: boolean,
): AttachmentSupport {
  if (attachment.classification === "inline") {
    return { kind: "unsupported", reason: "inline", supported: false };
  }
  const kind = attachmentKind(attachment.name, attachment.contentType);
  if (kind === "office" && !libreOfficeAvailable) {
    return { kind, reason: "libreoffice_required", supported: false };
  }
  if (kind === "unsupported") {
    return { kind, reason: "unsupported", supported: false };
  }
  return { kind, reason: "supported", supported: true };
}

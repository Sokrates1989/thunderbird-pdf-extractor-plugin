/** Attachment support tests keep review-time defaults aligned with native conversion scope. */

import { describe, expect, it } from "vitest";

import type { AttachmentSummary } from "../src/domain/models";
import { attachmentKind, attachmentSupport } from "../src/services/attachment-support";

function attachment(overrides: Partial<AttachmentSummary> = {}): AttachmentSummary {
  return {
    archiveIndex: 0,
    classification: "attachment",
    contentType: "application/octet-stream",
    index: 0,
    name: "unknown.bin",
    size: 10,
    ...overrides,
  };
}

describe("attachment conversion support", () => {
  it.each([
    ["invoice.pdf", "application/octet-stream", "pdf"],
    ["scan.tiff", "image/tiff", "image"],
    ["data.csv", "text/plain", "text"],
    ["page.html", "text/html", "html"],
    ["forwarded.eml", "message/rfc822", "eml"],
  ] as const)("classifies %s as %s", (name, contentType, expected) => {
    expect(attachmentKind(name, contentType)).toBe(expected);
  });

  it("requires local LibreOffice only for reviewed Office formats", () => {
    const office = attachment({ name: "report.docx" });
    expect(attachmentSupport(office, false)).toMatchObject({
      reason: "libreoffice_required",
      supported: false,
    });
    expect(attachmentSupport(office, true)).toMatchObject({
      kind: "office",
      supported: true,
    });
  });

  it("never selects inline images or unknown formats", () => {
    expect(attachmentSupport(attachment({ classification: "inline" }), true).supported).toBe(false);
    expect(attachmentSupport(attachment({ name: "archive.zip" }), true).supported).toBe(false);
  });
});

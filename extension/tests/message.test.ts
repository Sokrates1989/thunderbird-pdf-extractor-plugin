/** Selection tests ensure the extension never silently chooses among emails. */

import { describe, expect, it } from "vitest";

import { UserFacingError } from "../src/domain/errors";
import { requireSingleMessage, summarizeAttachments } from "../src/services/message";

const message: ThunderbirdMessageHeader = {
  author: "sender@example.test",
  date: new Date(2026, 7, 10),
  id: 42,
  subject: "Subject",
};

describe("single-message selection", () => {
  it("returns the only message", () => {
    expect(requireSingleMessage([message])).toBe(message);
  });

  const invalidSelections: readonly { readonly messages: readonly ThunderbirdMessageHeader[] }[] = [
    { messages: [] },
    { messages: [message, { ...message, id: 43 }] },
  ];

  it.each(invalidSelections)("rejects a selection that is not exactly one", ({ messages }) => {
    expect(() => requireSingleMessage(messages)).toThrow(UserFacingError);
  });
});

describe("attachment summaries", () => {
  it("assigns stable ordinals only to real attachments", () => {
    const summaries = summarizeAttachments([
      {
        contentId: "logo@example.test",
        contentType: "image/png",
        name: "logo.png",
        size: 1,
      },
      {
        contentDisposition: "attachment",
        contentType: "application/pdf",
        name: "first.pdf",
        size: 2,
      },
      {
        contentDisposition: "attachment",
        contentType: "text/plain",
        name: "second.txt",
        size: 3,
      },
    ]);

    expect(summaries.map(({ archiveIndex, classification }) => ({ archiveIndex, classification }))).toEqual([
      { archiveIndex: null, classification: "inline" },
      { archiveIndex: 0, classification: "attachment" },
      { archiveIndex: 1, classification: "attachment" },
    ]);
  });
});

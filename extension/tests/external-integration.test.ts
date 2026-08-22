import { describe, expect, it, vi } from "vitest";

import {
  AI_ASSISTANT_EXTENSION_ID,
  handleExternalIntegrationRequest,
  PDF_ARCHIVER_INTEGRATION_PROTOCOL_VERSION,
} from "../src/integration/external";

const trustedSender = { id: AI_ASSISTANT_EXTENSION_ID };

describe("AI Mail Assistant for Thunderbird integration", () => {
  it("does not expose the integration to untrusted extensions", async () => {
    const openReview = vi.fn(() => Promise.resolve());

    const response = await handleExternalIntegrationRequest(
      {
        messageId: 42,
        protocolVersion: PDF_ARCHIVER_INTEGRATION_PROTOCOL_VERSION,
        type: "thunderbird-pdf-archiver:open-review",
      },
      { id: "unknown@example.com" },
      openReview,
    );

    expect(response).toBeUndefined();
    expect(openReview).not.toHaveBeenCalled();
  });

  it("opens the existing review window for one validated Thunderbird message", async () => {
    const openReview = vi.fn(() => Promise.resolve());

    const response = await handleExternalIntegrationRequest(
      {
        messageId: 42,
        protocolVersion: PDF_ARCHIVER_INTEGRATION_PROTOCOL_VERSION,
        type: "thunderbird-pdf-archiver:open-review",
      },
      trustedSender,
      openReview,
    );

    expect(response).toEqual({ protocolVersion: 1, success: true });
    expect(openReview).toHaveBeenCalledOnce();
    expect(openReview).toHaveBeenCalledWith(42);
  });

  it("rejects incompatible protocols and invalid message IDs without side effects", async () => {
    const openReview = vi.fn(() => Promise.resolve());

    const incompatible = await handleExternalIntegrationRequest(
      { protocolVersion: 2, type: "thunderbird-pdf-archiver:ping" },
      trustedSender,
      openReview,
    );
    const invalid = await handleExternalIntegrationRequest(
      {
        messageId: -1,
        protocolVersion: PDF_ARCHIVER_INTEGRATION_PROTOCOL_VERSION,
        type: "thunderbird-pdf-archiver:open-review",
      },
      trustedSender,
      openReview,
    );

    expect(incompatible).toEqual({
      code: "unsupported_protocol",
      protocolVersion: 1,
      success: false,
    });
    expect(invalid).toEqual({ code: "invalid_request", protocolVersion: 1, success: false });
    expect(openReview).not.toHaveBeenCalled();
  });
});

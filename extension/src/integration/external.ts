/**
 * Defines the versioned cross-extension boundary used by AI Mail Assistant for Thunderbird.
 * Only the explicitly trusted companion extension may open the PDF review window.
 */

export const AI_ASSISTANT_EXTENSION_ID = "thunderbird-ai@felicitas-wisdom.com";
export const PDF_ARCHIVER_INTEGRATION_PROTOCOL_VERSION = 1;

export interface ExternalMessageSender {
  readonly id?: string;
}

export interface PdfArchiverIntegrationResponse {
  readonly code?: "invalid_request" | "open_failed" | "unsupported_protocol";
  readonly protocolVersion: number;
  readonly success: boolean;
}

export type OpenReviewWindow = (messageId: number) => Promise<void>;

/** Validate one external request before allowing it to trigger a review popup. */
export async function handleExternalIntegrationRequest(
  request: unknown,
  sender: ExternalMessageSender,
  openReviewWindow: OpenReviewWindow,
): Promise<PdfArchiverIntegrationResponse | undefined> {
  if (sender.id !== AI_ASSISTANT_EXTENSION_ID) {
    return undefined;
  }
  if (typeof request !== "object" || request === null || !("protocolVersion" in request)) {
    return failure("invalid_request");
  }
  if (request.protocolVersion !== PDF_ARCHIVER_INTEGRATION_PROTOCOL_VERSION) {
    return failure("unsupported_protocol");
  }
  if (!("type" in request) || typeof request.type !== "string") {
    return failure("invalid_request");
  }
  if (request.type === "thunderbird-pdf-archiver:ping") {
    return success();
  }
  if (request.type !== "thunderbird-pdf-archiver:open-review" || !("messageId" in request)) {
    return failure("invalid_request");
  }
  if (!Number.isSafeInteger(request.messageId) || Number(request.messageId) <= 0) {
    return failure("invalid_request");
  }
  try {
    await openReviewWindow(Number(request.messageId));
    return success();
  } catch {
    return failure("open_failed");
  }
}

function success(): PdfArchiverIntegrationResponse {
  return {
    protocolVersion: PDF_ARCHIVER_INTEGRATION_PROTOCOL_VERSION,
    success: true,
  };
}

function failure(code: NonNullable<PdfArchiverIntegrationResponse["code"]>): PdfArchiverIntegrationResponse {
  return {
    code,
    protocolVersion: PDF_ARCHIVER_INTEGRATION_PROTOCOL_VERSION,
    success: false,
  };
}

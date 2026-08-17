/** Versioned long-lived Native Messaging client for the local PDF companion. */

import { UserFacingError } from "../domain/errors";
import type { ArchiveMetadata } from "../domain/models";
import type { TransferPayload } from "../services/transfer";

const HOST_NAME = "de.sokrates1989.thunderbird_pdf_archiver";
const PROTOCOL_VERSION = "1.0";
export const EXTENSION_COMPONENT_VERSION = "0.5.0";
const RESPONSE_TIMEOUT_MILLISECONDS = 30_000;
const COMMIT_TIMEOUT_MILLISECONDS = 600_000;
const DIRECTORY_PICKER_TIMEOUT_MILLISECONDS = 600_000;

export interface ProgressUpdate {
  readonly completed: number;
  readonly detail: string;
  readonly stage: string;
  readonly total: number;
}

export interface ArchiveSuccess {
  readonly includedAttachments: readonly string[];
  readonly outputPath: string;
  readonly pageCount: number;
  readonly skippedAttachments: readonly string[];
}

export interface NativeCapabilities {
  readonly libreOfficeAvailable: boolean;
}

export interface NativeDiagnostics {
  readonly auditLogAvailable: boolean;
  readonly chromiumAvailable: boolean;
  readonly extensionVersion: string;
  readonly hostVersion: string;
  readonly libreOfficeAvailable: boolean;
  readonly outputDirectoryStatus: "not_configured" | "not_writable" | "writable";
  readonly packaged: boolean;
  readonly platform: "other" | "windows";
  readonly protocolVersion: string;
}

interface NativeResponse {
  readonly auditLogAvailable?: boolean;
  readonly chromiumAvailable?: boolean;
  readonly code?: string;
  readonly compatible?: boolean;
  readonly completed?: number;
  readonly detail?: string;
  readonly hostVersion?: string;
  readonly includedAttachments?: readonly string[];
  readonly index?: number;
  readonly jobId?: string;
  readonly message?: string;
  readonly libreOfficeAvailable?: boolean;
  readonly outputDirectory?: string;
  readonly outputDirectoryStatus?: string;
  readonly outputPath?: string;
  readonly pageCount?: number;
  readonly packaged?: boolean;
  readonly platform?: string;
  readonly protocolVersion?: string;
  readonly stage?: string;
  readonly selected?: boolean;
  readonly skippedAttachments?: readonly string[];
  readonly total?: number;
  readonly type: string;
}

interface PendingWaiter {
  readonly acceptedTypes: ReadonlySet<string>;
  readonly reject: (reason: Error) => void;
  readonly resolve: (response: NativeResponse) => void;
  readonly timer: number;
}

function parseResponse(value: unknown): NativeResponse {
  if (typeof value !== "object" || value === null || !("type" in value)) {
    throw new UserFacingError("invalid_host_response", "The native host returned an invalid response.");
  }
  const response = value as Record<string, unknown>;
  if (typeof response.type !== "string") {
    throw new UserFacingError("invalid_host_response", "The native host response has no valid type.");
  }
  return response as unknown as NativeResponse;
}

class ResponseInbox {
  readonly #messages: NativeResponse[] = [];
  readonly #waiters: PendingWaiter[] = [];

  public constructor(private readonly onProgress: (progress: ProgressUpdate) => void) {}

  public accept(value: unknown): void {
    let response: NativeResponse;
    try {
      response = parseResponse(value);
    } catch (error: unknown) {
      this.failAll(error instanceof Error ? error : new Error(String(error)));
      return;
    }

    if (response.type === "progress") {
      this.onProgress({
        completed: response.completed ?? 0,
        detail: response.detail ?? "",
        stage: response.stage ?? "unknown",
        total: response.total ?? 1,
      });
      return;
    }

    const waiterIndex = this.#waiters.findIndex(
      (waiter) => waiter.acceptedTypes.has(response.type) || response.type === "error",
    );
    if (waiterIndex < 0) {
      this.#messages.push(response);
      return;
    }
    const waiter = this.#waiters.splice(waiterIndex, 1)[0];
    if (waiter !== undefined) {
      clearTimeout(waiter.timer);
      waiter.resolve(response);
    }
  }

  public async waitFor(acceptedTypes: readonly string[], timeoutMilliseconds: number): Promise<NativeResponse> {
    const accepted = new Set(acceptedTypes);
    const queuedIndex = this.#messages.findIndex(
      (message) => accepted.has(message.type) || message.type === "error",
    );
    if (queuedIndex >= 0) {
      const queued = this.#messages.splice(queuedIndex, 1)[0];
      if (queued !== undefined) {
        return queued;
      }
    }

    return new Promise<NativeResponse>((resolve, reject) => {
      const timer = window.setTimeout(() => {
        const waiterIndex = this.#waiters.findIndex((waiter) => waiter.timer === timer);
        if (waiterIndex >= 0) {
          this.#waiters.splice(waiterIndex, 1);
        }
        reject(new UserFacingError("host_timeout", "The native host did not respond in time."));
      }, timeoutMilliseconds);
      this.#waiters.push({ acceptedTypes: accepted, reject, resolve, timer });
    });
  }

  public failAll(error: Error): void {
    for (const waiter of this.#waiters.splice(0)) {
      clearTimeout(waiter.timer);
      waiter.reject(error);
    }
  }
}

function requireSuccess(response: NativeResponse): NativeResponse {
  if (response.type === "error") {
    throw new UserFacingError(
      response.code ?? "native_host_error",
      response.message ?? "The native host reported an error.",
    );
  }
  return response;
}

function postAndWait(
  port: ThunderbirdNativePort,
  inbox: ResponseInbox,
  message: object,
  acceptedTypes: readonly string[],
  timeoutMilliseconds = RESPONSE_TIMEOUT_MILLISECONDS,
): Promise<NativeResponse> {
  const response = inbox.waitFor(acceptedTypes, timeoutMilliseconds);
  port.postMessage(message);
  return response;
}

async function handshake(port: ThunderbirdNativePort, inbox: ResponseInbox): Promise<NativeResponse> {
  const response = requireSuccess(
    await postAndWait(
      port,
      inbox,
      {
        componentVersion: EXTENSION_COMPONENT_VERSION,
        protocolVersion: PROTOCOL_VERSION,
        type: "hello",
      },
      ["hello"],
    ),
  );
  if (response.compatible !== true || response.protocolVersion !== PROTOCOL_VERSION) {
    throw new UserFacingError("incompatible_host", "The extension and native host versions are incompatible.");
  }
  return response;
}

function connect(onProgress: (progress: ProgressUpdate) => void): {
  readonly inbox: ResponseInbox;
  readonly port: ThunderbirdNativePort;
} {
  const port = browser.runtime.connectNative(HOST_NAME);
  const inbox = new ResponseInbox(onProgress);
  port.onMessage.addListener((message) => {
    inbox.accept(message);
  });
  port.onDisconnect.addListener((disconnectedPort) => {
    inbox.failAll(
      new UserFacingError(
        "host_disconnected",
        disconnectedPort.error?.message ?? "The native host disconnected unexpectedly.",
      ),
    );
  });
  return { inbox, port };
}

async function configure(
  port: ThunderbirdNativePort,
  inbox: ResponseInbox,
  outputDirectory: string,
): Promise<void> {
  requireSuccess(
    await postAndWait(
      port,
      inbox,
      { outputDirectory, protocolVersion: PROTOCOL_VERSION, type: "configure" },
      ["configured"],
    ),
  );
}

export class NativeArchiveClient {
  /** Query optional local converters before the user chooses attachments. */
  public async capabilities(): Promise<NativeCapabilities> {
    const { inbox, port } = connect(() => undefined);
    try {
      await handshake(port, inbox);
      const response = requireSuccess(
        await postAndWait(
          port,
          inbox,
          { protocolVersion: PROTOCOL_VERSION, type: "capabilities" },
          ["capabilities"],
        ),
      );
      return { libreOfficeAvailable: response.libreOfficeAvailable === true };
    } finally {
      port.disconnect();
    }
  }

  /** Build a path-free local support snapshot and verify the configured output folder. */
  public async diagnostics(outputDirectory: string): Promise<NativeDiagnostics> {
    const { inbox, port } = connect(() => undefined);
    try {
      await handshake(port, inbox);
      if (outputDirectory.length > 0) {
        await configure(port, inbox, outputDirectory);
      }
      const response = requireSuccess(
        await postAndWait(
          port,
          inbox,
          { protocolVersion: PROTOCOL_VERSION, type: "diagnostics" },
          ["diagnostics"],
        ),
      );
      const outputDirectoryStatus = response.outputDirectoryStatus;
      const platform = response.platform;
      if (
        typeof response.auditLogAvailable !== "boolean" ||
        typeof response.chromiumAvailable !== "boolean" ||
        typeof response.hostVersion !== "string" ||
        typeof response.libreOfficeAvailable !== "boolean" ||
        typeof response.packaged !== "boolean" ||
        typeof response.protocolVersion !== "string" ||
        !["not_configured", "not_writable", "writable"].includes(outputDirectoryStatus ?? "") ||
        !["other", "windows"].includes(platform ?? "")
      ) {
        throw new UserFacingError(
          "invalid_diagnostics_response",
          "The native host returned incomplete diagnostics.",
        );
      }
      return {
        auditLogAvailable: response.auditLogAvailable,
        chromiumAvailable: response.chromiumAvailable,
        extensionVersion: EXTENSION_COMPONENT_VERSION,
        hostVersion: response.hostVersion,
        libreOfficeAvailable: response.libreOfficeAvailable,
        outputDirectoryStatus: outputDirectoryStatus as NativeDiagnostics["outputDirectoryStatus"],
        packaged: response.packaged,
        platform: platform as NativeDiagnostics["platform"],
        protocolVersion: response.protocolVersion,
      };
    } finally {
      port.disconnect();
    }
  }

  /** Open the companion's native folder picker and return a selection or cancellation. */
  public async selectDirectory(initialDirectory: string, title: string): Promise<string | undefined> {
    const { inbox, port } = connect(() => undefined);
    try {
      await handshake(port, inbox);
      const response = requireSuccess(
        await postAndWait(
          port,
          inbox,
          {
            initialDirectory,
            protocolVersion: PROTOCOL_VERSION,
            title,
            type: "choose_directory",
          },
          ["directory_selected"],
          DIRECTORY_PICKER_TIMEOUT_MILLISECONDS,
        ),
      );
      if (response.selected !== true) {
        return undefined;
      }
      if (typeof response.outputDirectory !== "string" || response.outputDirectory.length === 0) {
        throw new UserFacingError(
          "invalid_directory_response",
          "The native host omitted the selected directory.",
        );
      }
      return response.outputDirectory;
    } finally {
      port.disconnect();
    }
  }

  /** Ask the companion to open its validated output directory in the Windows file manager. */
  public async openOutputDirectory(outputDirectory: string): Promise<void> {
    const { inbox, port } = connect(() => undefined);
    try {
      await handshake(port, inbox);
      await configure(port, inbox, outputDirectory);
      requireSuccess(
        await postAndWait(
          port,
          inbox,
          { protocolVersion: PROTOCOL_VERSION, type: "open_output_directory" },
          ["directory_opened"],
        ),
      );
    } finally {
      port.disconnect();
    }
  }

  public async checkConnection(outputDirectory: string): Promise<void> {
    const { inbox, port } = connect(() => undefined);
    try {
      await handshake(port, inbox);
      await configure(port, inbox, outputDirectory);
      requireSuccess(
        await postAndWait(
          port,
          inbox,
          { protocolVersion: PROTOCOL_VERSION, type: "connection_test" },
          ["connection_ok"],
        ),
      );
    } finally {
      port.disconnect();
    }
  }

  public async archive(
    transfer: TransferPayload,
    metadata: ArchiveMetadata,
    outputDirectory: string,
    signal: AbortSignal,
    onProgress: (progress: ProgressUpdate) => void,
  ): Promise<ArchiveSuccess> {
    const { inbox, port } = connect(onProgress);
    const jobId = crypto.randomUUID();
    const abort = (): void => {
      port.postMessage({ jobId, protocolVersion: PROTOCOL_VERSION, type: "cancel" });
      inbox.failAll(new DOMException("The archive operation was cancelled.", "AbortError"));
    };
    signal.addEventListener("abort", abort, { once: true });

    try {
      signal.throwIfAborted();
      await handshake(port, inbox);
      await configure(port, inbox, outputDirectory);
      requireSuccess(
        await postAndWait(
          port,
          inbox,
          {
            chunkCount: transfer.chunks.length,
            jobId,
            metadata,
            protocolVersion: PROTOCOL_VERSION,
            sha256: transfer.sha256,
            totalBytes: transfer.totalBytes,
            type: "archive_start",
          },
          ["archive_started"],
        ),
      );

      for (const [index, data] of transfer.chunks.entries()) {
        signal.throwIfAborted();
        const response = requireSuccess(
          await postAndWait(
            port,
            inbox,
            { data, index, jobId, protocolVersion: PROTOCOL_VERSION, type: "archive_chunk" },
            ["chunk_received"],
          ),
        );
        if (response.index !== index) {
          throw new UserFacingError("chunk_ack_mismatch", "The native host acknowledged the wrong chunk.");
        }
        onProgress({
          completed: index + 1,
          detail: "",
          stage: "transferring",
          total: transfer.chunks.length,
        });
      }

      const response = requireSuccess(
        await postAndWait(
          port,
          inbox,
          { jobId, protocolVersion: PROTOCOL_VERSION, type: "archive_commit" },
          ["success"],
          COMMIT_TIMEOUT_MILLISECONDS,
        ),
      );
      if (response.outputPath === undefined || response.pageCount === undefined) {
        throw new UserFacingError("invalid_success_response", "The native host omitted the output result.");
      }
      const includedAttachments = response.includedAttachments;
      const skippedAttachments = response.skippedAttachments;
      if (
        includedAttachments === undefined ||
        skippedAttachments === undefined ||
        !includedAttachments.every((item) => typeof item === "string") ||
        !skippedAttachments.every((item) => typeof item === "string")
      ) {
        throw new UserFacingError(
          "invalid_success_response",
          "The native host omitted the attachment result.",
        );
      }
      return {
        includedAttachments,
        outputPath: response.outputPath,
        pageCount: response.pageCount,
        skippedAttachments,
      };
    } finally {
      signal.removeEventListener("abort", abort);
      port.disconnect();
    }
  }
}

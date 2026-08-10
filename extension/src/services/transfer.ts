/** Bounded Base64 transfer preparation for Thunderbird Native Messaging. */

const KIBIBYTE = 1024;
const BASE64_BLOCK_BYTES = 32 * KIBIBYTE;
const HEX_RADIX = 16;

export const MAX_RAW_CHUNK_BYTES = 512 * KIBIBYTE;

export interface TransferPayload {
  readonly chunks: readonly string[];
  readonly sha256: string;
  readonly totalBytes: number;
}

function bytesToBase64(bytes: Uint8Array): string {
  const blocks: string[] = [];
  for (let offset = 0; offset < bytes.length; offset += BASE64_BLOCK_BYTES) {
    const block = bytes.subarray(offset, Math.min(offset + BASE64_BLOCK_BYTES, bytes.length));
    blocks.push(String.fromCharCode(...block));
  }
  return btoa(blocks.join(""));
}

export async function createTransferPayload(file: Blob): Promise<TransferPayload> {
  const content = new Uint8Array(await file.arrayBuffer());
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", content));
  const sha256 = Array.from(digest, (byte) => byte.toString(HEX_RADIX).padStart(2, "0")).join("");
  const chunks: string[] = [];

  for (let offset = 0; offset < content.length; offset += MAX_RAW_CHUNK_BYTES) {
    chunks.push(bytesToBase64(content.subarray(offset, offset + MAX_RAW_CHUNK_BYTES)));
  }

  return {
    chunks,
    sha256,
    totalBytes: content.length,
  };
}

/** Transfer tests verify chunk ceilings, reconstruction, byte count, and SHA-256. */

import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";

import { createTransferPayload, MAX_RAW_CHUNK_BYTES } from "../src/services/transfer";

function decodeBase64(value: string): Uint8Array {
  return Uint8Array.from(Buffer.from(value, "base64"));
}

describe("native transfer payload", () => {
  it("uses chunks no larger than 512 KiB and preserves content", async () => {
    const input = new Uint8Array(MAX_RAW_CHUNK_BYTES * 2 + 17);
    crypto.getRandomValues(input.subarray(0, 65_536));
    input.set(input.subarray(0, input.length - 65_536), 65_536);
    const payload = await createTransferPayload(new Blob([input]));
    const reconstructed = Buffer.concat(payload.chunks.map((chunk) => Buffer.from(decodeBase64(chunk))));

    expect(payload.chunks).toHaveLength(3);
    expect(payload.chunks.every((chunk) => decodeBase64(chunk).length <= MAX_RAW_CHUNK_BYTES)).toBe(true);
    expect(reconstructed).toEqual(Buffer.from(input));
    expect(payload.totalBytes).toBe(input.length);
    expect(payload.sha256).toBe(createHash("sha256").update(input).digest("hex"));
  });
});

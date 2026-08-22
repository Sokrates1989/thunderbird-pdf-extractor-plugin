/** Native-client error tests keep installer registration failures actionable. */

import { describe, expect, it } from "vitest";

import { nativeDisconnectCode } from "../src/protocol/native-client";

describe("native messaging disconnect diagnostics", () => {
  it.each([
    "No such native application de.sokrates1989.thunderbird_pdf_archiver",
    "Native host was not found",
    "The native messaging host is not registered",
    "Access to the specified native messaging host is forbidden",
  ])("identifies an unavailable native-host registration: %s", (message) => {
    expect(nativeDisconnectCode(message)).toBe("native_host_unavailable");
  });

  it("keeps a launched host crash distinct", () => {
    expect(nativeDisconnectCode("Native host has exited.")).toBe("host_disconnected");
  });
});

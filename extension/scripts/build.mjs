/** Build the extension's TypeScript entry points and copy reviewed static assets. */

import { cp, mkdir, rm } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { build } from "esbuild";

const extensionRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputDirectory = path.join(extensionRoot, "dist");

await rm(outputDirectory, { force: true, recursive: true });
if (process.argv.includes("--clean")) {
  process.exit(0);
}

await mkdir(outputDirectory, { recursive: true });

await build({
  bundle: true,
  entryPoints: {
    background: path.join(extensionRoot, "src", "background.ts"),
    "pages/options/options": path.join(extensionRoot, "src", "ui", "options.ts"),
    "pages/popup/popup": path.join(extensionRoot, "src", "ui", "popup.ts"),
  },
  format: "esm",
  logLevel: "info",
  outdir: outputDirectory,
  platform: "browser",
  sourcemap: true,
  target: "firefox128",
});

await cp(path.join(extensionRoot, "manifest.json"), path.join(outputDirectory, "manifest.json"));
await cp(path.join(extensionRoot, "pages"), path.join(outputDirectory, "pages"), { recursive: true });
await cp(path.join(extensionRoot, "_locales"), path.join(outputDirectory, "_locales"), { recursive: true });
await cp(path.join(extensionRoot, "assets"), path.join(outputDirectory, "assets"), { recursive: true });
await cp(
  path.join(extensionRoot, "install-defaults.json"),
  path.join(outputDirectory, "install-defaults.json"),
);

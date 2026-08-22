/** Package the built extension as a reproducible-root-layout XPI archive. */

import { createWriteStream } from "node:fs";
import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { ZipArchive } from "archiver";

const extensionRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(extensionRoot, "..");
const artifactDirectory = path.join(repositoryRoot, "artifacts");
const languageArgument = process.argv.find((argument) => argument.startsWith("--language="));
const language = languageArgument?.split("=")[1] ?? "auto";
if (!["auto", "de", "en"].includes(language)) {
  throw new Error(`Unsupported installer language '${language}'.`);
}
const languageSuffix = language === "auto" ? "" : `-${language}`;
const artifactPath = path.join(
  artifactDirectory,
  `thunderbird-pdf-archiver-1.1.0${languageSuffix}.xpi`,
);

await mkdir(artifactDirectory, { recursive: true });

await new Promise((resolve, reject) => {
  const output = createWriteStream(artifactPath);
  const archive = new ZipArchive({ zlib: { level: 9 } });

  output.on("close", resolve);
  output.on("error", reject);
  archive.on("error", reject);
  archive.pipe(output);
  archive.glob("**/*", {
    cwd: path.join(extensionRoot, "dist"),
    dot: true,
    ignore: ["install-defaults.json"],
  });
  archive.file(path.join(repositoryRoot, "LICENSE"), { name: "LICENSE" });
  archive.file(path.join(repositoryRoot, "THIRD_PARTY_NOTICES.md"), {
    name: "THIRD_PARTY_NOTICES.md",
  });
  archive.append(`${JSON.stringify({ language, version: "1.1.0" }, undefined, 2)}\n`, {
    name: "install-defaults.json",
  });
  void archive.finalize();
});

if (language === "auto") {
  await copyFile(artifactPath, path.join(artifactDirectory, "thunderbird-pdf-archiver.xpi"));
}

process.stdout.write(`${artifactPath}\n`);

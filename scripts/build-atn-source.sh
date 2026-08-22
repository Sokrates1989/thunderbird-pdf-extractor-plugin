#!/usr/bin/env bash
#
# Builds the source archive submitted to Thunderbird Add-ons reviewers.
#
set -euo pipefail

readonly SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/.." && pwd)"
readonly MANIFEST_PATH="${REPOSITORY_ROOT}/extension/manifest.json"

for command_name in git node zip unzip; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Required command not found: %s\n' "${command_name}" >&2
        exit 1
    }
done

version="$(node -e '
const fs = require("node:fs");
const manifest = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
if (!/^\d+\.\d+\.\d+$/.test(String(manifest.version))) {
  throw new Error("Manifest version is not semantic.");
}
process.stdout.write(manifest.version);
' "${MANIFEST_PATH}")"
artifact_directory="${REPOSITORY_ROOT}/artifacts"
output_path="${1:-${artifact_directory}/thunderbird-pdf-archiver-${version}-atn-source.zip}"
if [[ "${output_path}" != /* ]]; then
    output_path="$(pwd)/${output_path}"
fi

temporary_directory="$(mktemp -d "${TMPDIR:-/tmp}/thunderbird-pdf-atn-source.XXXXXX")"
trap 'rm -rf -- "${temporary_directory}"' EXIT
stage_directory="${temporary_directory}/source"
mkdir -p -- "${stage_directory}" "$(dirname -- "${output_path}")"

while IFS= read -r -d '' source_path; do
    [[ -f "${REPOSITORY_ROOT}/${source_path}" ]] || continue
    case "${source_path}" in
        *.p12|*.pfx|*.pem|*.key|id_rsa|id_ed25519|.env)
            printf 'Refusing to package credential-like tracked file: %s\n' "${source_path}" >&2
            exit 1
            ;;
        *.exe|*.pkg|*.xpi|*.zip)
            continue
            ;;
    esac
    destination_path="${stage_directory}/${source_path}"
    mkdir -p -- "$(dirname -- "${destination_path}")"
    cp -p -- "${REPOSITORY_ROOT}/${source_path}" "${destination_path}"
done < <(git -C "${REPOSITORY_ROOT}" ls-files --cached -z)

[[ -f "${stage_directory}/ATN_SOURCE_BUILD.md" ]] || {
    printf 'ATN_SOURCE_BUILD.md is missing from the tracked source set.\n' >&2
    exit 1
}

find "${stage_directory}" -type f -exec touch -t 200001010000 {} +
rm -f -- "${output_path}"
(
    cd -- "${stage_directory}"
    find . -type f -print | sed 's#^\./##' | LC_ALL=C sort | zip -X -q "${output_path}" -@
)
unzip -tq "${output_path}" >/dev/null
printf 'Created %s (%s bytes).\n' "${output_path}" "$(stat -f '%z' "${output_path}" 2>/dev/null || stat -c '%s' "${output_path}")"

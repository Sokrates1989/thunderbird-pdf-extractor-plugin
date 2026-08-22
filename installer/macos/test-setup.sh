#!/usr/bin/env bash
#
# Verifies the macOS package, native registration, and profile installation in isolation.
#
set -euo pipefail

readonly SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/../.." && pwd)"
readonly EXTENSION_ID='thunderbird-pdf@felicitas-wisdom.com'
readonly NATIVE_HOST_NAME='de.sokrates1989.thunderbird_pdf_archiver'

skip_build=false
build_arguments=()

print_usage() {
    printf 'Usage: %s [--skip-build] [build-setup.sh arguments]\n' "$0"
}

while (($# > 0)); do
    case "$1" in
        --skip-build)
            skip_build=true
            shift
            ;;
        --python|--sign)
            [[ $# -ge 2 ]] || { print_usage >&2; exit 2; }
            build_arguments+=("$1" "$2")
            shift 2
            ;;
        --skip-dependency-install|--skip-extension-build)
            build_arguments+=("$1")
            shift
            ;;
        --help|-h)
            print_usage
            exit 0
            ;;
        *)
            printf 'Unknown argument: %s\n' "$1" >&2
            print_usage >&2
            exit 2
            ;;
    esac
done

for command_name in installer node pkgutil unzip; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Required command not found: %s\n' "${command_name}" >&2
        exit 1
    }
done

if [[ "${skip_build}" == false ]]; then
    "${SCRIPT_DIRECTORY}/build-setup.sh" "${build_arguments[@]}"
fi

version="$(node -p 'require(process.argv[1]).version' \
    "${REPOSITORY_ROOT}/extension/manifest.json")"
architecture="$(uname -m)"
xpi_path="${REPOSITORY_ROOT}/artifacts/thunderbird-pdf-archiver-${version}.xpi"
host_path="${REPOSITORY_ROOT}/artifacts/native-host/macos-${architecture}/thunderbird-pdf-archiver-host"
package_path="${REPOSITORY_ROOT}/artifacts/Thunderbird-PDF-Archiver-Setup-${version}-macos-${architecture}.pkg"
for artifact_path in "${xpi_path}" "${host_path}" "${package_path}"; do
    [[ -f "${artifact_path}" ]] || {
        printf 'Required artifact is missing: %s\n' "${artifact_path}" >&2
        exit 1
    }
done

temporary_directory="$(mktemp -d "${TMPDIR:-/tmp}/thunderbird-pdf-archiver-installer-test.XXXXXX")"
trap 'rm -rf -- "${temporary_directory}"' EXIT
test_home="${temporary_directory}/home"
profiles_root="${test_home}/Library/Thunderbird/Profiles"
first_profile="${profiles_root}/fixture.default"
second_profile="${profiles_root}/fixture.default-esr"
payload_root="${temporary_directory}/payload"
manifest_directory="${test_home}/Library/Mozilla/NativeMessagingHosts"
manifest_path="${manifest_directory}/${NATIVE_HOST_NAME}.json"
legacy_manifest_directory="${test_home}/Library/Application Support/Mozilla/NativeMessagingHosts"
legacy_manifest_path="${legacy_manifest_directory}/${NATIVE_HOST_NAME}.json"
mkdir -p -- \
    "${first_profile}/extensions" "${second_profile}" "${payload_root}" \
    "${legacy_manifest_directory}"
install -m 0644 -- "${xpi_path}" "${payload_root}/thunderbird-pdf-archiver.xpi"
install -m 0755 -- "${host_path}" "${payload_root}/thunderbird-pdf-archiver-host"
printf '%s\n' "${version}" >"${payload_root}/VERSION"
printf 'old fixture\n' >"${first_profile}/extensions/${EXTENSION_ID}.xpi"
printf 'legacy fixture\n' >"${first_profile}/extensions/thunderbird-pdf-archiver@sokrates1989.de.xpi"
printf '{"legacy":true}\n' >"${legacy_manifest_path}"

THUNDERBIRD_PDF_ARCHIVER_INSTALL_HOME="${test_home}" \
THUNDERBIRD_PDF_ARCHIVER_PAYLOAD_ROOT="${payload_root}" \
    "${SCRIPT_DIRECTORY}/scripts/postinstall"

for profile_directory in "${first_profile}" "${second_profile}"; do
    installed_xpi="${profile_directory}/extensions/${EXTENSION_ID}.xpi"
    [[ -f "${installed_xpi}" ]] || {
        printf 'Profile XPI was not installed: %s\n' "${installed_xpi}" >&2
        exit 1
    }
    cmp -s "${xpi_path}" "${installed_xpi}" || {
        printf 'Installed profile XPI differs from the package payload.\n' >&2
        exit 1
    }
done
[[ ! -e "${legacy_manifest_path}" ]] || {
    printf 'Legacy macOS native-manifest registration was not removed.\n' >&2
    exit 1
}
[[ ! -e "${first_profile}/extensions/thunderbird-pdf-archiver@sokrates1989.de.xpi" ]] || {
    printf 'Legacy private extension identity was not removed.\n' >&2
    exit 1
}

node -e '
const fs = require("node:fs");
const manifest = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
if (manifest.name !== "de.sokrates1989.thunderbird_pdf_archiver" ||
    manifest.description !== "Thunderbird PDF Archiver native companion" ||
    manifest.path !== process.argv[2] || manifest.type !== "stdio" ||
    JSON.stringify(manifest.allowed_extensions) !==
        JSON.stringify(["thunderbird-pdf@felicitas-wisdom.com"])) {
    throw new Error("Installed native manifest is invalid.");
}
' "${manifest_path}" "${payload_root}/thunderbird-pdf-archiver-host"

defaults_json="$(unzip -p "${xpi_path}" install-defaults.json)"
node -e '
const defaults = JSON.parse(process.argv[1]);
if (defaults.language !== "auto" || defaults.version !== process.argv[2]) {
    throw new Error("macOS XPI contains unexpected install defaults.");
}
' "${defaults_json}" "${version}"
[[ "$("${host_path}" --version)" == "${version}" ]] || {
    printf 'Packaged native companion reports an unexpected version.\n' >&2
    exit 1
}

printf 'stale update fixture\n' >"${second_profile}/extensions/${EXTENSION_ID}.xpi"
printf '{"stale":true}\n' >"${manifest_path}"
mkdir -p -- "${legacy_manifest_directory}"
printf '{"legacy":true}\n' >"${legacy_manifest_path}"
THUNDERBIRD_PDF_ARCHIVER_INSTALL_HOME="${test_home}" \
THUNDERBIRD_PDF_ARCHIVER_PAYLOAD_ROOT="${payload_root}" \
    "${SCRIPT_DIRECTORY}/scripts/postinstall"
cmp -s "${xpi_path}" "${second_profile}/extensions/${EXTENSION_ID}.xpi" || {
    printf 'Second installation did not update the profile XPI.\n' >&2
    exit 1
}
node -e '
const fs = require("node:fs");
const manifest = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
if (manifest.path !== process.argv[2]) {
    throw new Error("Second installation did not repair the native manifest.");
}
' "${manifest_path}" "${payload_root}/thunderbird-pdf-archiver-host"
[[ ! -e "${legacy_manifest_path}" ]] || {
    printf 'Second installation did not remove the legacy native manifest.\n' >&2
    exit 1
}

missing_home="${temporary_directory}/missing-home"
mkdir -p -- "${missing_home}"
if THUNDERBIRD_PDF_ARCHIVER_INSTALL_HOME="${missing_home}" \
    THUNDERBIRD_PDF_ARCHIVER_PAYLOAD_ROOT="${payload_root}" \
    "${SCRIPT_DIRECTORY}/scripts/postinstall" >/dev/null 2>&1; then
    printf 'Postinstall unexpectedly accepted a home without Thunderbird profiles.\n' >&2
    exit 1
fi

expanded_product="${temporary_directory}/expanded-product"
pkgutil --expand "${package_path}" "${expanded_product}"
grep -F 'enable_currentUserHome="true"' "${expanded_product}/Distribution" >/dev/null
grep -F 'enable_localSystem="false"' "${expanded_product}/Distribution" >/dev/null
grep -F '<app id="org.mozilla.thunderbird"/>' "${expanded_product}/Distribution" >/dev/null
grep -F '<license file="LICENSE.txt" mime-type="text/plain"/>' \
    "${expanded_product}/Distribution" >/dev/null
cmp -s "${REPOSITORY_ROOT}/LICENSE" "${expanded_product}/Resources/LICENSE.txt" || {
    printf 'Product archive contains an unexpected license resource.\n' >&2
    exit 1
}
grep -F "version=\"${version}\"" "${expanded_product}/Distribution" >/dev/null
cmp -s \
    "${SCRIPT_DIRECTORY}/scripts/postinstall" \
    "${expanded_product}/Thunderbird-PDF-Archiver-component.pkg/Scripts/postinstall" || {
        printf 'Product archive contains an unexpected postinstall script.\n' >&2
        exit 1
    }
payload_files="$(pkgutil --payload-files "${package_path}")"
for required_payload in \
    'Library/Application Support/Thunderbird PDF Archiver/VERSION' \
    'Library/Application Support/Thunderbird PDF Archiver/LICENSE' \
    'Library/Application Support/Thunderbird PDF Archiver/THIRD_PARTY_NOTICES.md' \
    'Library/Application Support/Thunderbird PDF Archiver/thunderbird-pdf-archiver-host' \
    'Library/Application Support/Thunderbird PDF Archiver/thunderbird-pdf-archiver.xpi'; do
    printf '%s\n' "${payload_files}" | grep -F "${required_payload}" >/dev/null || {
        printf 'Package payload omits: %s\n' "${required_payload}" >&2
        exit 1
    }
done
cmp -s \
    "${package_path}" \
    "${REPOSITORY_ROOT}/artifacts/Thunderbird-PDF-Archiver-Setup-macos-${architecture}.pkg" || {
        printf 'Stable macOS release alias differs from the versioned package.\n' >&2
        exit 1
    }

domain_information="$(installer -dominfo -pkg "${package_path}")"
printf '%s\n' "${domain_information}" | grep -F 'CurrentUserHomeDirectory' >/dev/null
if printf '%s\n' "${domain_information}" | grep -F 'LocalSystem' >/dev/null; then
    printf 'macOS package unexpectedly permits a system-wide install.\n' >&2
    exit 1
fi

printf 'Isolated Thunderbird PDF Archiver macOS install/update and package verification: PASS\n'

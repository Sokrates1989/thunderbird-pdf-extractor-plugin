#!/usr/bin/env bash
#
# Builds the per-user macOS Installer package, XPI, and native companion.
#
set -euo pipefail
export COPYFILE_DISABLE=1

readonly SCRIPT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIRECTORY}/../.." && pwd)"

skip_dependency_install=false
skip_extension_build=false
python_candidate="${PYTHON_3_12:-python3.12}"
signing_identity=''

print_usage() {
    printf 'Usage: %s [--python PATH] [--skip-dependency-install] [--skip-extension-build] [--sign IDENTITY]\n' "$0"
}

while (($# > 0)); do
    case "$1" in
        --python)
            [[ $# -ge 2 ]] || { print_usage >&2; exit 2; }
            python_candidate="$2"
            shift 2
            ;;
        --skip-dependency-install)
            skip_dependency_install=true
            shift
            ;;
        --skip-extension-build)
            skip_extension_build=true
            shift
            ;;
        --sign)
            [[ $# -ge 2 ]] || { print_usage >&2; exit 2; }
            signing_identity="$2"
            shift 2
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

for command_name in codesign lipo node npm pkgbuild productbuild pkgutil unzip xattr xmllint; do
    command -v "${command_name}" >/dev/null 2>&1 || {
        printf 'Required command not found: %s\n' "${command_name}" >&2
        exit 1
    }
done

if [[ "${python_candidate}" == */* ]]; then
    [[ -x "${python_candidate}" ]] || {
        printf 'Python 3.12 executable not found: %s\n' "${python_candidate}" >&2
        exit 1
    }
    resolved_python="${python_candidate}"
else
    resolved_python="$(command -v "${python_candidate}" || true)"
    [[ -n "${resolved_python}" ]] || {
        printf 'Python 3.12 was not found. Pass --python PATH or set PYTHON_3_12.\n' >&2
        exit 1
    }
fi
"${resolved_python}" -c \
    'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)' || {
    printf 'The macOS native companion requires Python 3.12: %s\n' "${resolved_python}" >&2
    exit 1
}

architecture="$(uname -m)"
case "${architecture}" in
    arm64|x86_64) ;;
    *)
        printf 'Unsupported macOS architecture: %s\n' "${architecture}" >&2
        exit 1
        ;;
esac

extension_root="${REPOSITORY_ROOT}/extension"
native_root="${REPOSITORY_ROOT}/native-host"
virtual_environment="${native_root}/.venv"
venv_python="${virtual_environment}/bin/python"
artifact_root="${REPOSITORY_ROOT}/artifacts"

version="$(node -e '
const fs = require("node:fs");
const path = require("node:path");
const root = process.argv[1];
const manifest = JSON.parse(fs.readFileSync(path.join(root, "extension/manifest.json"), "utf8"));
const packageJson = JSON.parse(fs.readFileSync(path.join(root, "extension/package.json"), "utf8"));
const defaults = JSON.parse(fs.readFileSync(path.join(root, "extension/install-defaults.json"), "utf8"));
const nativeSource = fs.readFileSync(path.join(root, "native-host/paperless_mail_archiver/__init__.py"), "utf8");
const nativeVersion = nativeSource.match(/__version__ = "([^"]+)"/)?.[1];
const versions = [manifest.version, packageJson.version, defaults.version, nativeVersion];
if (!versions.every(version => /^\d+\.\d+\.\d+$/.test(String(version))) ||
    !versions.every(version => version === versions[0])) {
    throw new Error(`Component versions are not synchronized: ${versions.join(", ")}`);
}
if (manifest.browser_specific_settings?.gecko?.id !==
    "thunderbird-pdf@felicitas-wisdom.com") {
    throw new Error("Manifest extension ID does not match the installer identity.");
}
process.stdout.write(manifest.version);
' "${REPOSITORY_ROOT}")"

if [[ "${skip_dependency_install}" == false ]]; then
    (cd -- "${extension_root}" && npm ci)
    if [[ ! -x "${venv_python}" ]]; then
        "${resolved_python}" -m venv "${virtual_environment}"
    fi
    "${venv_python}" -c \
        'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)' || {
        printf 'Existing native-host virtual environment is not Python 3.12: %s\n' \
            "${virtual_environment}" >&2
        exit 1
    }
    "${venv_python}" -m pip install --require-hashes \
        -r "${native_root}/requirements-macos.lock"
fi

[[ -x "${venv_python}" ]] || {
    printf 'Native-host virtual environment is missing: %s\n' "${venv_python}" >&2
    exit 1
}
[[ -d "${extension_root}/node_modules" ]] || {
    printf 'Extension dependencies are missing: %s\n' "${extension_root}/node_modules" >&2
    exit 1
}

xpi_path="${artifact_root}/thunderbird-pdf-archiver-${version}.xpi"
if [[ "${skip_extension_build}" == false ]]; then
    (cd -- "${extension_root}" && npm run build && node scripts/package.mjs)
fi
[[ -f "${xpi_path}" ]] || {
    printf 'Required XPI not found: %s\n' "${xpi_path}" >&2
    exit 1
}

unzip -p "${xpi_path}" manifest.json | node -e '
let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => { input += chunk; });
process.stdin.on("end", () => {
    const manifest = JSON.parse(input);
    if (manifest.version !== process.argv[1] ||
        manifest.browser_specific_settings?.gecko?.id !==
            "thunderbird-pdf@felicitas-wisdom.com") {
        throw new Error("Packaged XPI does not match the source manifest.");
    }
});
' "${version}"
for required_entry in LICENSE THIRD_PARTY_NOTICES.md; do
    unzip -Z1 "${xpi_path}" | grep -Fx "${required_entry}" >/dev/null || {
        printf 'XPI omits required publication entry: %s\n' "${required_entry}" >&2
        exit 1
    }
done
unzip -p "${xpi_path}" install-defaults.json | node -e '
let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => { input += chunk; });
process.stdin.on("end", () => {
    const defaults = JSON.parse(input);
    if (defaults.language !== "auto" || defaults.version !== process.argv[1]) {
        throw new Error("macOS XPI contains unexpected install defaults.");
    }
});
' "${version}"

temporary_directory="$(mktemp -d "${TMPDIR:-/tmp}/thunderbird-pdf-archiver-pkg.XXXXXX")"
trap 'rm -rf -- "${temporary_directory}"' EXIT
published_native_root="${artifact_root}/native-host/macos-${architecture}"
published_native_artifact="${published_native_root}/thunderbird-pdf-archiver-host"
native_artifact_root="${temporary_directory}/native-dist"
native_artifact="${native_artifact_root}/thunderbird-pdf-archiver-host"
pyinstaller_work="${temporary_directory}/pyinstaller-work"
pyinstaller_spec="${temporary_directory}/pyinstaller-spec"
pyinstaller_config="${temporary_directory}/pyinstaller-config"
mkdir -p -- \
    "${native_artifact_root}" "${pyinstaller_work}" "${pyinstaller_spec}" \
    "${pyinstaller_config}"
(cd -- "${native_root}" && PYINSTALLER_CONFIG_DIR="${pyinstaller_config}" \
    "${venv_python}" -m PyInstaller \
    --clean \
    --noconfirm \
    --onefile \
    --target-arch "${architecture}" \
    --name 'thunderbird-pdf-archiver-host' \
    --distpath "${native_artifact_root}" \
    --workpath "${pyinstaller_work}" \
    --specpath "${pyinstaller_spec}" \
    "${native_root}/main.py")

[[ -x "${native_artifact}" ]] || {
    printf 'Native companion build is missing: %s\n' "${native_artifact}" >&2
    exit 1
}
reported_version="$("${native_artifact}" --version)"
[[ "${reported_version}" == "${version}" ]] || {
    printf 'Native companion version %s does not match %s.\n' \
        "${reported_version}" "${version}" >&2
    exit 1
}
lipo "${native_artifact}" -verify_arch "${architecture}"
codesign --verify --deep --strict "${native_artifact}"
mkdir -p -- "${published_native_root}"
install -m 0755 -- "${native_artifact}" "${published_native_artifact}"
xattr -cr "${published_native_artifact}"

payload_root="${temporary_directory}/payload"
payload_directory="${payload_root}/Library/Application Support/Thunderbird PDF Archiver"
component_package="${temporary_directory}/Thunderbird-PDF-Archiver-component.pkg"
distribution_path="${temporary_directory}/distribution.xml"
expanded_package="${temporary_directory}/expanded"
resources_directory="${temporary_directory}/resources"
mkdir -p -- "${payload_directory}"
install -m 0644 -- "${xpi_path}" "${payload_directory}/thunderbird-pdf-archiver.xpi"
install -m 0755 -- "${native_artifact}" "${payload_directory}/thunderbird-pdf-archiver-host"
install -m 0644 -- "${REPOSITORY_ROOT}/LICENSE" "${payload_directory}/LICENSE"
install -m 0644 -- "${REPOSITORY_ROOT}/THIRD_PARTY_NOTICES.md" \
    "${payload_directory}/THIRD_PARTY_NOTICES.md"
printf '%s\n' "${version}" >"${payload_directory}/VERSION"
cp -R -- "${SCRIPT_DIRECTORY}/resources" "${resources_directory}"
install -m 0644 -- "${REPOSITORY_ROOT}/LICENSE" "${resources_directory}/LICENSE.txt"
xattr -cr "${payload_root}"

sed "s/@APP_VERSION@/${version}/g" \
    "${SCRIPT_DIRECTORY}/distribution.xml" >"${distribution_path}"
xmllint --noout "${distribution_path}"

pkgbuild \
    --root "${payload_root}" \
    --scripts "${SCRIPT_DIRECTORY}/scripts" \
    --identifier 'com.sokrates1989.thunderbird-pdf-archiver' \
    --version "${version}" \
    --install-location '/' \
    "${component_package}"

output_path="${artifact_root}/Thunderbird-PDF-Archiver-Setup-${version}-macos-${architecture}.pkg"
mkdir -p -- "${artifact_root}"
rm -f -- "${output_path}"
productbuild_arguments=(
    --distribution "${distribution_path}"
    --resources "${resources_directory}"
    --package-path "${temporary_directory}"
)
if [[ -n "${signing_identity}" ]]; then
    productbuild_arguments+=(--sign "${signing_identity}")
fi
productbuild "${productbuild_arguments[@]}" "${output_path}"

stable_output_path="${artifact_root}/Thunderbird-PDF-Archiver-Setup-macos-${architecture}.pkg"
cp -- "${output_path}" "${stable_output_path}"

pkgutil --expand "${output_path}" "${expanded_package}"
xmllint --noout "${expanded_package}/Distribution"
[[ -d "${expanded_package}/Thunderbird-PDF-Archiver-component.pkg" ]] || {
    printf 'Product archive omits its component package.\n' >&2
    exit 1
}

printf 'Created %s (%s bytes).\n' "${output_path}" "$(stat -f '%z' "${output_path}")"
printf 'Created stable release alias %s.\n' "${stable_output_path}"

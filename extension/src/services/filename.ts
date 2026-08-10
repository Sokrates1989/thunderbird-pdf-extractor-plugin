/** Human-readable title and Windows-safe PDF filename generation. */

const MAX_FILENAME_LENGTH = 180;
const YEAR_WIDTH = 4;
const RESERVED_WINDOWS_NAMES = /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$/iu;

export function senderDisplayName(author: string): string {
  const angleBracketIndex = author.lastIndexOf("<");
  const candidate = angleBracketIndex > 0 ? author.slice(0, angleBracketIndex) : author;
  const unquoted = candidate.trim().replace(/^['"]|['"]$/gu, "");
  return unquoted.length > 0 ? unquoted : author.trim();
}

export function defaultTitle(date: Date, author: string, subject: string): string {
  const datePart = [
    String(date.getFullYear()).padStart(YEAR_WIDTH, "0"),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
  const normalizedSubject = subject.trim().length > 0 ? subject.trim() : "E-Mail";
  return `${datePart} - ${senderDisplayName(author)} - ${normalizedSubject}`;
}

export function sanitizePdfFileName(title: string): string {
  const normalized = title
    .normalize("NFC")
    // The explicit C0 range is required because Windows rejects those characters.
    // eslint-disable-next-line no-control-regex
    .replace(/[<>:"/\\|?*\u0000-\u001F]/gu, "_")
    .replace(/\s+/gu, " ")
    .trim()
    .replace(/[. ]+$/gu, "");
  const baseName = normalized.length > 0 ? normalized : "E-Mail";
  const safeBaseName = RESERVED_WINDOWS_NAMES.test(baseName) ? `_${baseName}` : baseName;
  const maxBaseLength = MAX_FILENAME_LENGTH - ".pdf".length;
  const truncated = safeBaseName.slice(0, maxBaseLength).replace(/[. ]+$/gu, "");
  return `${truncated}.pdf`;
}

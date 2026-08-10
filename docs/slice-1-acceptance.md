# Slice 1 acceptance contract

Slice 1 is considered directionally correct when all of these statements hold:

- exactly one explicitly displayed or selected Thunderbird message is used;
- the review shows safe metadata and all detected attachments;
- attachment rows and the generated PDF state clearly that attachments are not
  yet included;
- the raw decrypted EML crosses the native boundary in bounded, ordered,
  checksummed chunks;
- the PDF contains normalized metadata and readable, searchable body text, not
  raw MIME headers or Base64 payloads;
- multipart/alternative content is not duplicated;
- placeholder mode performs no image request; embed mode resolves only bounded
  safe raster sources and falls back per image;
- rendered email HTML cannot fetch remote resources or execute active content;
- a native folder picker can select the destination, and the success view can
  open that validated folder;
- a complete PDF is saved only to the configured existing directory and never
  overwrites another file;
- cancellation and failures clean temporary message/rendering data; and
- TypeScript/Python type checks, lint, tests, production builds, and packaging
  complete without errors.

Attachment conversion/merging and any Paperless upload are explicit non-criteria
for this slice. The next slice should begin only after the manual Thunderbird
matrix in `testing.md` confirms this interaction and architecture.

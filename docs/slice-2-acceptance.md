# Slice 2 acceptance contract

Slice 2 is accepted when a real Thunderbird test demonstrates all of the
following:

- exactly one reviewed email produces one local PDF without changing the email;
- all supported real attachments are selected by default and can be deselected;
- inline body images are never duplicated as attachment sections;
- unsupported and intentionally skipped files are visible before save, in the
  email section, and in the final result;
- selected PDF, image, TXT/CSV, HTML, and nested EML inputs are converted and
  merged after the email in original MIME order;
- PDF pages remain non-rasterized with original size/orientation and searchable
  text where present;
- every included attachment has a correct PDF outline entry;
- optional separator pages default off and work when enabled;
- Office/ODF selection accurately follows local LibreOffice availability;
- selected corrupt, password-required, unsafe, or failed input aborts with its
  filename rather than disappearing, while empty-user-password PDFs merge after
  normalization;
- cancellation and failure leave no partial final PDF or message/attachment temp
  data; and
- the success action opens the configured destination folder.

Automated coverage establishes converter, merge, security, and protocol
behavior. It does not by itself satisfy the cross-version Thunderbird acceptance
matrix in [testing.md](testing.md).

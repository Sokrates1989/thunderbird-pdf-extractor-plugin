"""PDF assembly tests enforce the narrow interactive-action security boundary."""

from io import BytesIO
from pathlib import Path
from threading import Event
from typing import cast

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, TextStringObject

from paperless_mail_archiver.email_parser import parse_email
from paperless_mail_archiver.pdf_assembler import PdfSection, assemble_pdf
from tests.helpers import plain_email_bytes, searchable_pdf_bytes


def _pdf_with_mixed_actions() -> bytes:
    """Create one safe URI link plus JavaScript, file, and page actions."""
    reader = PdfReader(BytesIO(searchable_pdf_bytes()))
    writer = PdfWriter()
    writer.append(reader, import_outline=False)
    page = writer.pages[0]
    script_action = DictionaryObject(
        {
            NameObject("/S"): NameObject("/JavaScript"),
            NameObject("/JS"): TextStringObject("app.alert('unsafe')"),
        }
    )
    unsafe_link = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject(
                (NumberObject(10), NumberObject(10), NumberObject(80), NumberObject(30))
            ),
            NameObject("/A"): script_action,
        }
    )
    file_link = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject(
                (NumberObject(90), NumberObject(10), NumberObject(160), NumberObject(30))
            ),
            NameObject("/A"): DictionaryObject(
                {
                    NameObject("/S"): NameObject("/URI"),
                    NameObject("/URI"): TextStringObject("file:///C:/private.txt"),
                }
            ),
        }
    )
    annotations = cast(ArrayObject, page["/Annots"])
    annotations.extend((unsafe_link, file_link))
    page[NameObject("/AA")] = DictionaryObject({NameObject("/O"): script_action})
    output = BytesIO()
    writer.write(output)
    writer.close()
    return output.getvalue()


def test_assembler_preserves_only_normalized_uri_link_actions(tmp_path: Path) -> None:
    """Safe external links survive while JavaScript and additional actions are removed."""
    source = tmp_path / "mixed-actions.pdf"
    source.write_bytes(_pdf_with_mixed_actions())
    target = tmp_path / "assembled.pdf"

    assemble_pdf(
        target,
        (PdfSection(title="Source", path=source),),
        parse_email(plain_email_bytes()),
        title="Safe links",
        separator_pages=False,
        cancellation=Event(),
    )

    page = PdfReader(target).pages[0]
    assert "/AA" not in page
    annotations = cast(ArrayObject, page["/Annots"])
    assert len(annotations) == 1
    annotation = cast(DictionaryObject, annotations[0].get_object())
    action = cast(DictionaryObject, annotation["/A"])
    assert str(action["/S"]) == "/URI"
    assert str(action["/URI"]) == "https://example.test/active-link"
    assert "/JS" not in annotation
    assert "/Next" not in action

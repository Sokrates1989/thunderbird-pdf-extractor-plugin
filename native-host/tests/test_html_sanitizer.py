"""Sanitizer tests prove active content and remote-loadable attributes are removed."""

from paperless_mail_archiver.html_sanitizer import html_to_text, sanitize_html
from paperless_mail_archiver.image_resources import ResolvedImage
from tests.helpers import VALID_PNG


def test_sanitizer_removes_active_and_remote_content() -> None:
    """Scripts, handlers, CSS, forms, and image sources cannot reach Chromium."""
    fragment = """
      <style>@import url(https://tracker.invalid/style.css)</style>
      <script>fetch('https://tracker.invalid/script')</script>
      <form action="https://tracker.invalid/form"><input name="secret"></form>
      <p onclick="alert(1)">Readable <strong>content</strong></p>
      <img src="https://tracker.invalid/pixel" alt="Company logo">
    """
    sanitized = sanitize_html(fragment)

    assert 'href="https://tracker.invalid/pixel"' in sanitized
    assert 'src="https://tracker.invalid/pixel"' not in sanitized
    assert "script" not in sanitized
    assert "onclick" not in sanitized
    assert "Readable <strong>content</strong>" in sanitized
    assert "Company logo" in sanitized
    assert "image-placeholder" in sanitized


def test_links_remain_visible_in_fallback_text() -> None:
    """Safe printable links preserve their readable anchor label."""
    sanitized = sanitize_html('<p>See <a href="https://example.test/invoice">invoice</a>.</p>')

    assert 'href="https://example.test/invoice"' in sanitized
    assert html_to_text(sanitized) == "See invoice."


def test_remote_image_placeholder_links_to_its_safe_source() -> None:
    """A standalone remote-image fallback remains inert while its label is clickable."""
    sanitized = sanitize_html(
        '<img src="https://images.example.test/recipe.png?size=large" alt="Recipe photo">'
    )

    assert sanitized == (
        '<a class="image-link" href="https://images.example.test/recipe.png?size=large">'
        '<span class="image-placeholder">[Recipe photo]</span></a>'
    )


def test_remote_image_inside_link_uses_the_existing_safe_destination() -> None:
    """An image fallback never creates invalid nested anchors inside an existing link."""
    sanitized = sanitize_html(
        '<a href="https://example.test/recipe"><img '
        'src="https://images.example.test/recipe.png" alt="Recipe photo"></a>'
    )

    assert sanitized.count("<a ") == 1
    assert 'href="https://example.test/recipe"' in sanitized
    assert 'class="image-link"' in sanitized
    assert 'href="https://images.example.test/recipe.png"' not in sanitized


def test_unsafe_image_source_does_not_become_a_link() -> None:
    """Unsupported image schemes remain plain placeholders without PDF actions."""
    sanitized = sanitize_html('<img src="file:///private/logo.png" alt="Logo">')

    assert sanitized == '<span class="image-placeholder">[Logo]</span>'


def test_resolved_image_is_embedded_and_image_link_does_not_print_tracking_url() -> None:
    """A resolver can embed verified data and mark an enclosing link as image-only."""
    sanitized = sanitize_html(
        '<a href="https://tracker.invalid/click"><img src="cid:logo" alt="Logo"></a>',
        lambda _source: ResolvedImage(content_type="image/png", data=VALID_PNG),
    )

    assert 'class="image-link"' in sanitized
    assert 'src="data:image/png;base64,' in sanitized
    assert "cid:logo" not in sanitized

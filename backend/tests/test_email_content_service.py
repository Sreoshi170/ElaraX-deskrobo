"""Regression tests for safe email text rendering."""

from backend.graphs.email.nodes import summary_node
from backend.services.email_content_service import sanitize_email_content


def test_sanitizer_removes_html_css_and_collapses_whitespace() -> None:
    content = """
    <html><head><style>body { font-family: Arial; color: red; }</style></head>
    <body><div>Hello <strong>ElaraX</strong></div><script>alert('x')</script></body></html>
    """

    clean = sanitize_email_content(content)

    assert clean == "Hello ElaraX"
    assert "<" not in clean
    assert "font-family" not in clean


def test_summary_fallback_never_echoes_raw_html(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.generate_text",
        lambda **kwargs: None,
    )

    result = summary_node(
        {
            "retrieved_emails": [
                {
                    "sender": "marketing@example.com",
                    "subject": "Offer",
                    "body": "<style>.hero { font-family: Arial; }</style><p>Save 20% this week.</p>",
                }
            ]
        }
    )

    assert "Save 20% this week." in result["email_summary"]
    assert "<style>" not in result["email_summary"]
    assert "font-family" not in result["email_summary"]


def test_summary_sanitizes_model_output_that_echoes_email_html(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.graphs.email.nodes.gemini_reasoning_service.generate_text",
        lambda **kwargs: "<style>.hero { font-family: Arial; }</style><p>Save 20% this week.</p>",
    )

    result = summary_node(
        {
            "retrieved_emails": [
                {
                    "sender": "marketing@example.com",
                    "subject": "Offer",
                    "body": "<p>Save 20% this week.</p>",
                }
            ]
        }
    )

    assert result["email_summary"] == "Save 20% this week."

from app.services.rag_service import sanitize_ai_text


def test_sanitize_ai_text_replaces_generated_image_filenames():
    raw = "Review Gemini_Generated_Image_abc123.png and invoice_001.png"
    cleaned = sanitize_ai_text(raw)
    assert "Gemini_Generated_Image_abc123.png" not in cleaned
    assert "Generated image" in cleaned
    assert "invoice" in cleaned

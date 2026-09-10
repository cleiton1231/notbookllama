from app.services.vector_store import _chroma_metadata


def test_chroma_metadata_omits_none():
    cleaned = _chroma_metadata({"filename": "a.txt", "total_pages": None, "ocr_used": False})
    assert "total_pages" not in cleaned
    assert cleaned["filename"] == "a.txt"
    assert cleaned["ocr_used"] is False

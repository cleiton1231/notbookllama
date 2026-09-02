import io
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pypdf import PdfWriter

# Imports from app services
from app.services.ocr_parser import (
    extract_text_ocr,
    extract_pdf_pages_ocr,
    is_ocr_available,
    OCRResult,
    _run_ocr_pipeline,
    _run_ocr_on_images,
)
from app.services.document_parser import sanitize_filename, calculate_sha256


def create_sample_pdf() -> bytes:
    """Helper to create a valid minimal in-memory PDF."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


class TestOCRParser:
    """Test suite for OCR fallback local parser."""

    def test_ocr_result_class(self):
        """Test OCRResult data container and serialization."""
        res = OCRResult(text="Exemplo de texto", ocr_used=True, pages_count=2, error=None)
        assert res.text == "Exemplo de texto"
        assert res.ocr_used is True
        assert res.pages_count == 2
        d = res.to_dict()
        assert d["text"] == "Exemplo de texto"
        assert d["ocr_used"] is True
        assert d["pages_count"] == 2
        assert d["error"] is None

    def test_is_ocr_available(self):
        """Checks OCR availability detection for presence and absence of binaries."""
        with patch("shutil.which") as mock_which:
            mock_which.side_effect = lambda cmd: "/usr/bin/" + cmd if cmd in ["pdftoppm", "tesseract"] else None
            assert is_ocr_available() is True

            mock_which.side_effect = lambda cmd: "/usr/bin/pdftoppm" if cmd == "pdftoppm" else None
            assert is_ocr_available() is False

            mock_which.side_effect = lambda cmd: None
            assert is_ocr_available() is False

    def test_extract_text_ocr_above_threshold(self, tmp_path):
        """When PDF has sufficient digital text, OCR is NOT invoked (ocr_used=False)."""
        pdf_file = tmp_path / "normal_doc.pdf"
        pdf_file.write_bytes(create_sample_pdf())

        sample_text = "This is a document with plenty of searchable digital text that exceeds the threshold easily."

        with patch("app.services.ocr_parser.PdfReader") as mock_reader, \
             patch("app.services.ocr_parser._run_ocr_pipeline") as mock_ocr:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = sample_text
            mock_reader.return_value.pages = [mock_page]

            text, ocr_used = extract_text_ocr(pdf_file, min_chars_threshold=50)
            assert ocr_used is False
            assert "searchable digital text" in text
            mock_ocr.assert_not_called()

    def test_extract_text_ocr_below_threshold_triggers_ocr(self, tmp_path):
        """When PDF text is below threshold, OCR extraction is attempted."""
        pdf_file = tmp_path / "scanned_doc.pdf"
        pdf_file.write_bytes(create_sample_pdf())

        with patch("app.services.ocr_parser.PdfReader") as mock_reader, \
             patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), \
             patch("app.services.ocr_parser._run_ocr_pipeline") as mock_ocr_pipeline:
            
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "   "  # Below threshold (0 chars)
            mock_reader.return_value.pages = [mock_page]
            mock_ocr_pipeline.return_value = ("Texto extraído via OCR com sucesso", True)

            text, ocr_used = extract_text_ocr(pdf_file, min_chars_threshold=50)
            assert ocr_used is True
            assert text == "Texto extraído via OCR com sucesso"
            mock_ocr_pipeline.assert_called_once()

    def test_extract_text_ocr_missing_tesseract_fallback(self, tmp_path):
        """When tesseract binary is not installed, returns clean diagnostic message."""
        pdf_file = tmp_path / "scanned_no_tesseract.pdf"
        pdf_file.write_bytes(create_sample_pdf())

        with patch("app.services.ocr_parser.PdfReader") as mock_reader, \
             patch("shutil.which", return_value=None):
            
            mock_page = MagicMock()
            mock_page.extract_text.return_value = ""
            mock_reader.return_value.pages = [mock_page]

            text, ocr_used = extract_text_ocr(pdf_file, min_chars_threshold=50)
            assert ocr_used is False
            assert "[Aviso: OCR indisponível" in text or "tesseract" in text.lower()

    def test_extract_text_ocr_missing_pdftoppm_fallback(self, tmp_path):
        """When pdftoppm is missing but tesseract is present, returns diagnostic."""
        pdf_file = tmp_path / "scanned_no_pdftoppm.pdf"
        pdf_file.write_bytes(create_sample_pdf())

        def mock_which_pdftoppm(cmd):
            if cmd == "tesseract":
                return "/usr/bin/tesseract"
            return None

        with patch("app.services.ocr_parser.PdfReader") as mock_reader, \
             patch("shutil.which", side_effect=mock_which_pdftoppm):
            
            mock_page = MagicMock()
            mock_page.extract_text.return_value = ""
            mock_reader.return_value.pages = [mock_page]

            text, ocr_used = extract_text_ocr(pdf_file, min_chars_threshold=50)
            assert ocr_used is False
            assert "pdftoppm" in text.lower() or "indisponível" in text.lower()

    def test_extract_text_ocr_corrupted_pdf(self, tmp_path):
        """Corrupted PDF returns safe diagnostic string without crashing."""
        corrupt_file = tmp_path / "corrupt.pdf"
        corrupt_file.write_bytes(b"This is not a real PDF header at all...")

        text, ocr_used = extract_text_ocr(corrupt_file)
        assert ocr_used is False
        assert "[Erro:" in text or "corrompido" in text.lower() or "inválido" in text.lower()

    def test_extract_text_ocr_nonexistent_file(self, tmp_path):
        """Nonexistent file path returns error message."""
        missing = tmp_path / "nonexistent.pdf"
        text, ocr_used = extract_text_ocr(missing)
        assert ocr_used is False
        assert "[Erro: Arquivo não encontrado" in text

    def test_extract_text_ocr_empty_content(self, tmp_path):
        """Empty 0-byte file handled safely."""
        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")

        text, ocr_used = extract_text_ocr(empty_file)
        assert ocr_used is False
        assert "[Erro:" in text or "vazio" in text.lower()

    def test_extract_text_ocr_accepts_bytes_directly(self):
        """extract_text_ocr supports passing raw bytes directly."""
        sample_bytes = create_sample_pdf()

        with patch("app.services.ocr_parser.PdfReader") as mock_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Valid digital text extracted directly from raw bytes content."
            mock_reader.return_value.pages = [mock_page]

            text, ocr_used = extract_text_ocr(sample_bytes, min_chars_threshold=20)
            assert ocr_used is False
            assert "Valid digital text" in text

    def test_extract_text_ocr_empty_bytes(self):
        """extract_text_ocr returns error on empty bytes."""
        text, ocr_used = extract_text_ocr(b"")
        assert ocr_used is False
        assert "[Erro:" in text

    def test_extract_text_ocr_custom_threshold(self, tmp_path):
        """Custom threshold is respected when deciding whether to trigger OCR."""
        pdf_file = tmp_path / "threshold_test.pdf"
        pdf_file.write_bytes(create_sample_pdf())
        short_text = "Short text (24 chars)."

        with patch("app.services.ocr_parser.PdfReader") as mock_reader, \
             patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), \
             patch("app.services.ocr_parser._run_ocr_pipeline") as mock_ocr_pipeline:
            
            mock_page = MagicMock()
            mock_page.extract_text.return_value = short_text
            mock_reader.return_value.pages = [mock_page]
            mock_ocr_pipeline.return_value = ("OCR Extracted Content", True)

            # Threshold 10: 24 >= 10 -> No OCR needed
            text, ocr_used = extract_text_ocr(pdf_file, min_chars_threshold=10)
            assert ocr_used is False
            assert text == short_text
            mock_ocr_pipeline.assert_not_called()

            # Threshold 50: 24 < 50 -> Triggers OCR pipeline
            text, ocr_used = extract_text_ocr(pdf_file, min_chars_threshold=50)
            assert ocr_used is True
            assert text == "OCR Extracted Content"
            mock_ocr_pipeline.assert_called_once()

    def test_extract_pdf_pages_ocr_multipage(self, tmp_path):
        """Test page-by-page OCR extraction helper."""
        pdf_file = tmp_path / "multipage.pdf"
        pdf_file.write_bytes(create_sample_pdf())

        with patch("app.services.ocr_parser.PdfReader") as mock_reader, \
             patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), \
             patch("app.services.ocr_parser._run_ocr_on_images") as mock_ocr_img:
            
            p1 = MagicMock()
            p1.extract_text.return_value = "Page 1 has plenty of normal text that exceeds threshold."
            p2 = MagicMock()
            p2.extract_text.return_value = ""  # Image page
            mock_reader.return_value.pages = [p1, p2]
            mock_ocr_img.return_value = "Page 2 OCR text content"

            pages_result = extract_pdf_pages_ocr(pdf_file, min_chars_threshold=30)
            assert len(pages_result) == 2
            assert pages_result[0]["page_number"] == 1
            assert pages_result[0]["ocr_used"] is False
            assert "Page 1 has plenty" in str(pages_result[0]["text"])

    def test_extract_pdf_pages_ocr_bytes_input(self):
        """Test page-by-page OCR extraction with raw bytes."""
        sample_bytes = create_sample_pdf()

        with patch("app.services.ocr_parser.PdfReader") as mock_reader:
            p1 = MagicMock()
            p1.extract_text.return_value = "Single page digital text content here."
            mock_reader.return_value.pages = [p1]

            pages = extract_pdf_pages_ocr(sample_bytes, min_chars_threshold=10)
            assert len(pages) == 1
            assert pages[0]["page_number"] == 1
            assert pages[0]["ocr_used"] is False
            assert "Single page digital text" in str(pages[0]["text"])

    def test_preserves_sha256_and_filename_sanitization(self):
        """Ensures document parser dedupe SHA-256 and sanitization rules match."""
        raw_content = b"Simulated PDF content for hash check"
        sha256_hash = calculate_sha256(raw_content)
        assert len(sha256_hash) == 64
        assert calculate_sha256(raw_content) == calculate_sha256(raw_content)

        unsafe_name = "../../etc/passwd/scanned_report.pdf"
        safe_name = sanitize_filename(unsafe_name)
        assert ".." not in safe_name
        assert safe_name == "scanned_report.pdf"

    def test_ocr_pipeline_execution_success(self, tmp_path):
        """Tests internal OCR pipeline using subprocess mocking with tools present."""
        sample_pdf = tmp_path / "sample.pdf"
        sample_pdf.write_bytes(b"%PDF-1.4 mock content")

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), \
             patch("subprocess.run") as mock_run:
            # Mock pdftoppm generating image files
            def side_effect(cmd, **kwargs):
                if cmd[0] == "pdftoppm":
                    out_prefix = cmd[-1]
                    img_file = Path(f"{out_prefix}-1.png")
                    img_file.write_bytes(b"mock_png_bytes")
                    return MagicMock(returncode=0, stdout="", stderr="")
                elif cmd[0] == "tesseract":
                    return MagicMock(returncode=0, stdout="Extracted OCR text line 1\nExtracted OCR text line 2", stderr="")
                return MagicMock(returncode=0, stdout="", stderr="")

            mock_run.side_effect = side_effect

            text, ocr_used = _run_ocr_pipeline(sample_pdf)
            assert ocr_used is True
            assert "Extracted OCR text line 1" in text

    def test_ocr_pipeline_subprocess_timeout(self, tmp_path):
        """OCR subprocess timeout during pdftoppm is handled gracefully."""
        import subprocess

        sample_pdf = tmp_path / "timeout.pdf"
        sample_pdf.write_bytes(b"%PDF-1.4 mock")

        with patch("shutil.which", side_effect=lambda cmd: f"/usr/bin/{cmd}"), \
             patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pdftoppm", timeout=30)):
            text, ocr_used = _run_ocr_pipeline(sample_pdf)
            assert ocr_used is False
            assert "[Erro:" in text or "tempo limite" in text.lower() or "timeout" in text.lower()

    def test_run_ocr_on_images_with_fallback(self, tmp_path):
        """Test OCR on image files with language fallback if first attempt fails."""
        img1 = tmp_path / "test-1.png"
        img1.write_bytes(b"image_content")

        calls = []
        def mock_subp(cmd, **kwargs):
            calls.append(cmd)
            if "-l" in cmd:
                # Simulate missing Portuguese language pack
                return MagicMock(returncode=1, stdout="", stderr="Error: por tessdata missing")
            return MagicMock(returncode=0, stdout="Fallback English text result", stderr="")

        with patch("subprocess.run", side_effect=mock_subp):
            result = _run_ocr_on_images([img1], lang="por+eng")
            assert "Fallback English text result" in result
            assert len(calls) == 2  # First with lang, second fallback without

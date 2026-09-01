import hashlib
import io
from pathlib import Path
from typing import List, Tuple, Optional
from pypdf import PdfReader


class ParsedPage:
    def __init__(self, page_number: int, text: str):
        self.page_number = page_number
        self.text = text


class ParsedDocument:
    def __init__(self, filename: str, file_type: str, file_size: int, sha256: str, pages: List[ParsedPage]):
        self.filename = filename
        self.file_type = file_type
        self.file_size = file_size
        self.sha256 = sha256
        self.pages = pages
        self.total_pages = len(pages)


def calculate_sha256(content: bytes) -> str:
    """Calcula hash SHA-256 dos bytes do arquivo para desduplicação."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()


def parse_pdf(content: bytes, filename: str) -> List[ParsedPage]:
    """Extrai texto e número de páginas de um arquivo PDF."""
    pdf_file = io.BytesIO(content)
    reader = PdfReader(pdf_file)
    pages = []
    for idx, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        # Limpar quebras excessivas preservando parágrafos
        cleaned_text = page_text.strip()
        if cleaned_text:
            pages.append(ParsedPage(page_number=idx + 1, text=cleaned_text))
    
    if not pages:
        # Se for PDF sem camada de texto legível
        pages.append(ParsedPage(page_number=1, text="[Aviso: PDF sem camada de texto legível]"))
    return pages


def parse_plain_text(content: bytes, filename: str) -> List[ParsedPage]:
    """Decodifica arquivos de texto (TXT, MD) com suporte a UTF-8 e fallbacks."""
    encodings = ["utf-8", "latin-1", "cp1252"]
    text = ""
    for enc in encodings:
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    
    if not text:
        text = content.decode("utf-8", errors="replace")
    
    return [ParsedPage(page_number=1, text=text.strip())]


def parse_document(content: bytes, filename: str) -> ParsedDocument:
    """Extrai texto e metadados estruturados do arquivo de acordo com a extensão."""
    ext = Path(filename).suffix.lower()
    file_size = len(content)
    sha256_hash = calculate_sha256(content)

    if ext == ".pdf":
        pages = parse_pdf(content, filename)
        file_type = "pdf"
    elif ext in [".md", ".markdown"]:
        pages = parse_plain_text(content, filename)
        file_type = "markdown"
    elif ext in [".txt", ".log", ".csv", ".json"]:
        pages = parse_plain_text(content, filename)
        file_type = "text"
    else:
        # Fallback genérico para arquivos com texto
        pages = parse_plain_text(content, filename)
        file_type = "generic_text"

    return ParsedDocument(
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        sha256=sha256_hash,
        pages=pages
    )

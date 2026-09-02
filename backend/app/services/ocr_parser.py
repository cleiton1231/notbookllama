import io
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)


class OCRResult:
    """Estrutura com o resultado da extração de OCR."""
    def __init__(self, text: str, ocr_used: bool, pages_count: int = 1, error: Optional[str] = None):
        self.text = text
        self.ocr_used = ocr_used
        self.pages_count = pages_count
        self.error = error

    def to_dict(self) -> Dict[str, Union[str, bool, int, Optional[str]]]:
        return {
            "text": self.text,
            "ocr_used": self.ocr_used,
            "pages_count": self.pages_count,
            "error": self.error,
        }


def is_ocr_available() -> bool:
    """
    Verifica se os utilitários de OCR locais necessários estão disponíveis no sistema.
    Requer 'pdftoppm' (para renderizar páginas em imagens) e 'tesseract' (para OCR).
    """
    has_pdftoppm = shutil.which("pdftoppm") is not None
    has_tesseract = shutil.which("tesseract") is not None
    return bool(has_pdftoppm and has_tesseract)


def _check_ocr_tool_diagnostics() -> Optional[str]:
    """Retorna mensagem diagnóstica caso ferramentas de OCR não estejam instaladas."""
    has_pdftoppm = shutil.which("pdftoppm") is not None
    has_tesseract = shutil.which("tesseract") is not None

    if not has_pdftoppm and not has_tesseract:
        return "[Aviso: PDF sem camada de texto e OCR indisponível - ferramentas pdftoppm e tesseract não instaladas no sistema]"
    if not has_pdftoppm:
        return "[Aviso: PDF sem camada de texto e ferramenta de conversão de imagem (pdftoppm) indisponível no sistema]"
    if not has_tesseract:
        return "[Aviso: PDF sem camada de texto e OCR indisponível - tesseract não instalado no sistema]"
    return None


def _run_ocr_on_images(image_paths: List[Path], lang: str = "por+eng") -> str:
    """
    Executa o tesseract local em uma lista de caminhos de imagens e concatena o texto.
    Tenta primeiro com o idioma solicitado, com fallback para o padrão do tesseract se faltar tessdata.
    """
    extracted_pages: List[str] = []

    for img_path in sorted(image_paths):
        if not img_path.exists() or img_path.stat().st_size == 0:
            continue

        cmd = ["tesseract", str(img_path), "stdout"]
        if lang:
            cmd.extend(["-l", lang])

        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                check=False,
            )
            if res.returncode != 0:
                # Tentar fallback sem parâmetro de idioma caso falte pacote de idiomas
                fallback_cmd = ["tesseract", str(img_path), "stdout"]
                res = subprocess.run(
                    fallback_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30,
                    check=False,
                )

            page_text = res.stdout.strip() if res.stdout else ""
            if page_text:
                extracted_pages.append(page_text)
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout no OCR da imagem: {img_path.name}")
            continue
        except Exception as e:
            logger.warning(f"Erro ao processar imagem no OCR: {e}")
            continue

    return "\n\n".join(extracted_pages).strip()


def _run_ocr_pipeline(pdf_path: Path, lang: str = "por+eng") -> Tuple[str, bool]:
    """
    Pipeline completo de OCR:
    1. Converte PDF para imagens PNG via pdftoppm em diretório temporário isolado.
    2. Executa OCR em cada imagem via tesseract.
    3. Retorna o texto consolidado e a flag booleana de sucesso.
    """
    diagnostic = _check_ocr_tool_diagnostics()
    if diagnostic:
        return diagnostic, False

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        output_prefix = temp_dir / "page"

        # Converte páginas do PDF para PNGs a 150 DPI
        pdftoppm_cmd = [
            "pdftoppm",
            "-png",
            "-r", "150",
            str(pdf_path),
            str(output_prefix),
        ]

        try:
            proc = subprocess.run(
                pdftoppm_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                check=False,
            )
            if proc.returncode != 0:
                return (
                    f"[Erro na renderização de páginas do PDF via pdftoppm: {proc.stderr.strip()}]",
                    False,
                )
        except subprocess.TimeoutExpired:
            return "[Erro: Tempo limite excedido ao renderizar páginas do PDF via pdftoppm]", False
        except Exception as e:
            return f"[Erro ao converter PDF para imagem: {e}]", False

        # Localiza as imagens geradas
        image_files = sorted(temp_dir.glob("page-*.png"))
        if not image_files:
            return "[Aviso: Nenhuma imagem foi gerada a partir do PDF para processamento OCR]", False

        ocr_text = _run_ocr_on_images(image_files, lang=lang)
        if not ocr_text:
            return "[Aviso: OCR executado com sucesso, mas nenhum texto foi detectado nas imagens]", True

        return ocr_text, True


def extract_text_ocr(
    file_path: Union[Path, str, bytes],
    min_chars_threshold: int = 50,
    lang: str = "por+eng",
) -> Tuple[str, bool]:
    """
    Extrai texto de um documento PDF, acionando OCR local quando o texto digital
    extraído pelo pypdf estiver abaixo do limite configurado (min_chars_threshold).

    Args:
        file_path: Caminho do arquivo (Path/str) ou bytes brutos do PDF.
        min_chars_threshold: Quantidade mínima de caracteres para considerar o PDF legível sem OCR.
        lang: Idiomas para o tesseract (padrão 'por+eng').

    Returns:
        Tuple[str, bool]: (texto_extraido, ocr_utilizado_bool)
    """
    # Se receber bytes diretamente, gravar em arquivo temporário seguro
    temp_file_cleanup: Optional[Path] = None
    target_path: Path

    if isinstance(file_path, bytes):
        if not file_path:
            return "[Erro: Conteúdo do arquivo PDF está vazio ou inválido]", False
        temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        temp_file.write(file_path)
        temp_file.flush()
        temp_file.close()
        target_path = Path(temp_file.name)
        temp_file_cleanup = target_path
    else:
        target_path = Path(file_path)
        if not target_path.exists():
            return f"[Erro: Arquivo não encontrado: {target_path.name}]", False
        if target_path.stat().st_size == 0:
            return "[Erro: Arquivo PDF está vazio (0 bytes)]", False

    try:
        # 1. Tentar leitura nativa com pypdf
        extracted_pages: List[str] = []
        try:
            reader = PdfReader(str(target_path))
            for page in reader.pages:
                txt = page.extract_text() or ""
                cleaned = txt.strip()
                if cleaned:
                    extracted_pages.append(cleaned)
        except (PdfReadError, Exception) as parse_err:
            logger.warning(f"Falha na leitura padrão pypdf: {parse_err}")
            # Se pypdf falhar por arquivo corrompido ou formato inválido
            return f"[Erro: Arquivo PDF corrompido ou formato inválido: {parse_err}]", False

        combined_digital_text = "\n\n".join(extracted_pages).strip()

        # 2. Se o texto digital for suficiente, retornar sem OCR
        if len(combined_digital_text) >= min_chars_threshold:
            return combined_digital_text, False

        # 3. Texto abaixo do limite: acionar OCR fallback local
        ocr_text, ocr_success = _run_ocr_pipeline(target_path, lang=lang)
        if ocr_success:
            return ocr_text, True

        # Se OCR falhou ou ferramentas não disponíveis, mas havia algum texto digital
        if combined_digital_text:
            return combined_digital_text, False

        # Caso contrário, retorna o diagnóstico do OCR
        return ocr_text, False

    finally:
        # Limpeza segura do arquivo temporário se criado
        if temp_file_cleanup and temp_file_cleanup.exists():
            try:
                temp_file_cleanup.unlink()
            except OSError:
                pass


def extract_pdf_pages_ocr(
    content_or_path: Union[bytes, Path, str],
    min_chars_threshold: int = 50,
    lang: str = "por+eng",
) -> List[Dict[str, Union[int, str, bool]]]:
    """
    Extrai páginas estruturadas com detecção granular de OCR por página.
    Ideal para integração direta em `document_parser.py` (retornando lista compatível com ParsedPage).

    Returns:
        List[Dict]: [{'page_number': 1, 'text': '...', 'ocr_used': False}, ...]
    """
    temp_file_cleanup: Optional[Path] = None
    target_path: Path

    if isinstance(content_or_path, bytes):
        if not content_or_path:
            return [{"page_number": 1, "text": "[Erro: PDF vazio]", "ocr_used": False}]
        temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        temp_file.write(content_or_path)
        temp_file.flush()
        temp_file.close()
        target_path = Path(temp_file.name)
        temp_file_cleanup = target_path
    else:
        target_path = Path(content_or_path)
        if not target_path.exists() or target_path.stat().st_size == 0:
            return [{"page_number": 1, "text": "[Erro: Arquivo inexistente ou vazio]", "ocr_used": False}]

    results: List[Dict[str, Union[int, str, bool]]] = []

    try:
        try:
            reader = PdfReader(str(target_path))
            total_pages = len(reader.pages)
        except Exception as e:
            return [{"page_number": 1, "text": f"[Erro: PDF corrompido: {e}]", "ocr_used": False}]

        if total_pages == 0:
            return [{"page_number": 1, "text": "[Aviso: PDF sem páginas]", "ocr_used": False}]

        # Se OCR estiver disponível, renderizar páginas se alguma precisar de OCR
        ocr_available = is_ocr_available()

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            digital_text = (page.extract_text() or "").strip()

            if len(digital_text) >= min_chars_threshold:
                results.append({
                    "page_number": page_num,
                    "text": digital_text,
                    "ocr_used": False,
                })
            elif ocr_available:
                # Extrair OCR para página específica
                with tempfile.TemporaryDirectory() as page_temp_dir:
                    page_temp = Path(page_temp_dir)
                    out_pref = page_temp / "page"
                    cmd = [
                        "pdftoppm",
                        "-png",
                        "-f", str(page_num),
                        "-l", str(page_num),
                        "-r", "150",
                        str(target_path),
                        str(out_pref),
                    ]
                    try:
                        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False)
                        imgs = list(page_temp.glob("page-*.png"))
                        page_ocr_text = _run_ocr_on_images(imgs, lang=lang) if imgs else ""
                    except Exception:
                        page_ocr_text = ""

                if page_ocr_text:
                    results.append({
                        "page_number": page_num,
                        "text": page_ocr_text,
                        "ocr_used": True,
                    })
                elif digital_text:
                    results.append({
                        "page_number": page_num,
                        "text": digital_text,
                        "ocr_used": False,
                    })
                else:
                    results.append({
                        "page_number": page_num,
                        "text": "[Aviso: Página sem camada de texto legível]",
                        "ocr_used": False,
                    })
            else:
                # OCR não disponível
                if digital_text:
                    results.append({
                        "page_number": page_num,
                        "text": digital_text,
                        "ocr_used": False,
                    })
                else:
                    results.append({
                        "page_number": page_num,
                        "text": "[Aviso: Página sem camada de texto legível e OCR indisponível]",
                        "ocr_used": False,
                    })

        return results

    finally:
        if temp_file_cleanup and temp_file_cleanup.exists():
            try:
                temp_file_cleanup.unlink()
            except OSError:
                pass

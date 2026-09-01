from typing import List, Optional
import uuid
from app.schemas import DocumentChunk
from app.services.document_parser import ParsedDocument


def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 60
) -> List[str]:
    """
    Divide texto respeitando parágrafos e frases com sobreposição (overlap).
    Garante que nenhum chunk exceda o limite configurado.
    """
    if not text or not text.strip():
        return []

    # Dividir primeiro por quebras duplas de parágrafo
    paragraphs = text.split("\n\n")
    raw_blocks: List[str] = []
    
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        if len(p_clean) <= chunk_size:
            raw_blocks.append(p_clean)
        else:
            # Dividir parágrafos longos por frases ou linhas
            lines = p_clean.split("\n")
            for line in lines:
                l_clean = line.strip()
                if not l_clean:
                    continue
                if len(l_clean) <= chunk_size:
                    raw_blocks.append(l_clean)
                else:
                    # Dividir por sentenças ou corte estrito
                    words = l_clean.split(" ")
                    current = []
                    current_len = 0
                    for w in words:
                        if current_len + len(w) + 1 > chunk_size and current:
                            raw_blocks.append(" ".join(current))
                            current = [w]
                            current_len = len(w)
                        else:
                            current.append(w)
                            current_len += len(w) + 1
                    if current:
                        raw_blocks.append(" ".join(current))

    # Agora agrupar blocos com overlap
    chunks: List[str] = []
    current_chunk = ""

    for block in raw_blocks:
        if not current_chunk:
            current_chunk = block
        elif len(current_chunk) + len(block) + 2 <= chunk_size:
            current_chunk += "\n\n" + block
        else:
            chunks.append(current_chunk)
            # Aplicar overlap pegando o sufixo do chunk anterior
            if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                overlap_text = current_chunk[-chunk_overlap:]
                # Tentar começar na primeira palavra completa do overlap
                first_space = overlap_text.find(" ")
                if first_space != -1:
                    overlap_text = overlap_text[first_space + 1:]
                current_chunk = overlap_text + "\n" + block
            else:
                current_chunk = block

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def create_document_chunks(
    parsed_doc: ParsedDocument,
    doc_id: str,
    chunk_size: int = 500,
    chunk_overlap: int = 60
) -> List[DocumentChunk]:
    """Gera chunks estruturados e identificados para todas as páginas do documento."""
    document_chunks: List[DocumentChunk] = []
    global_index = 0

    for page in parsed_doc.pages:
        text_chunks = split_text_into_chunks(page.text, chunk_size, chunk_overlap)
        for chunk_text in text_chunks:
            chunk_id = f"{doc_id}_c{global_index}"
            document_chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    filename=parsed_doc.filename,
                    chunk_index=global_index,
                    page_number=page.page_number,
                    content=chunk_text,
                    char_count=len(chunk_text)
                )
            )
            global_index += 1

    return document_chunks

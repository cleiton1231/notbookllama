import math
import re
import unicodedata
from collections import Counter, defaultdict

from app.schemas import DocumentChunk

# Conjunto de stopwords frequentes (Português e Inglês)
STOPWORDS: set[str] = {
    # Português
    "a", "ao", "aos", "aquela", "aquelas", "aquele", "aqueles", "aquilo", "as", "à", "às",
    "ate", "com", "como", "da", "das", "de", "dela", "delas", "dele", "deles", "depois",
    "do", "dos", "e", "ela", "elas", "ele", "eles", "em", "entre", "era", "eram", "eramos",
    "essa", "essas", "esse", "esses", "esta", "estas", "este", "estes", "estive", "estou",
    "estao", "eu", "foi", "fomos", "foram", "ha", "isso", "isto", "ja", "lhe", "lhes",
    "mais", "mas", "me", "mesmo", "meu", "meus", "minha", "minhas", "muito", "na", "nas",
    "nao", "nem", "no", "nos", "nossa", "nossas", "nosso", "nossos", "num", "numa",
    "o", "os", "ou", "para", "pela", "pelas", "pelo", "pelos", "por", "qual", "quando",
    "que", "quem", "sao", "se", "seja", "sejam", "sem", "sera", "serao", "seu", "seus",
    "so", "sua", "suas", "tambem", "te", "tem", "temos", "ter", "teu", "teus", "tinha",
    "tinham", "tive", "tu", "tua", "tuas", "um", "uma", "voce", "voces",
    # Inglês
    "an", "and", "are", "at", "be", "by", "for", "from", "has", "he", "in", "is",
    "it", "its", "of", "on", "that", "the", "to", "was", "were", "will", "with"
}


def strip_accents(text: str) -> str:
    """Remove marcas diacríticas/acentos de strings unicode."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def tokenize(
    text: str,
    remove_stopwords: bool = False,
    normalize_accents: bool = True
) -> list[str]:
    """
    Tokeniza o texto em palavras alfanuméricas minúsculas.
    Remove pontuação e opcionalmente normaliza acentos e remove stopwords.
    """
    if not text:
        return []

    clean_text = text.lower()
    if normalize_accents:
        clean_text = strip_accents(clean_text)

    # Identifica sequências alfanuméricas e palavras unicode (incluindo hífen e sublinhado no corpo)
    tokens = re.findall(r"\b[\w\-]+\b", clean_text)

    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]

    return tokens


class BM25Search:
    """
    Implementação pura em Python do algoritmo Okapi BM25 para recuperação lexical
    sobre chunks de documentos (DocumentChunk) sem dependências externas.
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        remove_stopwords: bool = False,
        normalize_accents: bool = True
    ):
        self.k1 = k1
        self.b = b
        self.remove_stopwords = remove_stopwords
        self.normalize_accents = normalize_accents

        # Estruturas de índice invertido e metadados
        self.chunks: dict[str, DocumentChunk] = {}
        self.doc_chunks: dict[str, set[str]] = defaultdict(set)
        self.doc_lengths: dict[str, int] = {}
        self.doc_term_freqs: dict[str, Counter] = {}
        self.inverted_index: dict[str, set[str]] = defaultdict(set)

        self.total_chunks: int = 0
        self.avgdl: float = 0.0
        self._idf_cache: dict[str, float] | None = None

    def tokenize_text(self, text: str) -> list[str]:
        """Tokeniza usando as configurações configuradas nesta instância."""
        return tokenize(
            text,
            remove_stopwords=self.remove_stopwords,
            normalize_accents=self.normalize_accents
        )

    def _recalculate_stats(self) -> None:
        """Recalcula comprimento médio dos documentos e limpa cache de IDF."""
        self.total_chunks = len(self.chunks)
        if self.total_chunks > 0:
            total_tokens = sum(self.doc_lengths.values())
            self.avgdl = total_tokens / self.total_chunks
        else:
            self.avgdl = 0.0
        self._idf_cache = None

    def index_chunks(self, chunks: list[DocumentChunk]) -> None:
        """
        Substitui o índice atual indexando a lista de chunks fornecida.
        """
        self.clear()
        self.add_chunks(chunks)

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """
        Adiciona chunks ao índice existente, atualizando estruturas e estatísticas.
        """
        if not chunks:
            return

        for chunk in chunks:
            cid = chunk.chunk_id
            tokens = self.tokenize_text(chunk.content)
            tf = Counter(tokens)

            # Se o chunk já existia anteriormente, remove do inverted_index antes de atualizar
            if cid in self.chunks:
                old_tf = self.doc_term_freqs.get(cid, {})
                for old_term in old_tf:
                    self.inverted_index[old_term].discard(cid)
                    if not self.inverted_index[old_term]:
                        del self.inverted_index[old_term]

            self.chunks[cid] = chunk
            self.doc_chunks[chunk.doc_id].add(cid)
            self.doc_lengths[cid] = len(tokens)
            self.doc_term_freqs[cid] = tf

            for term in tf:
                self.inverted_index[term].add(cid)

        self._recalculate_stats()

    def remove_document(self, doc_id: str) -> None:
        """
        Remove todos os chunks associados a um doc_id específico.
        """
        cids_to_remove = list(self.doc_chunks.get(doc_id, set()))
        if not cids_to_remove:
            return

        for cid in cids_to_remove:
            tf = self.doc_term_freqs.get(cid, {})
            for term in tf:
                self.inverted_index[term].discard(cid)
                if not self.inverted_index[term]:
                    del self.inverted_index[term]

            self.chunks.pop(cid, None)
            self.doc_lengths.pop(cid, None)
            self.doc_term_freqs.pop(cid, None)

        self.doc_chunks.pop(doc_id, None)
        self._recalculate_stats()

    def clear(self) -> None:
        """Limpa completamente todos os dados do índice."""
        self.chunks.clear()
        self.doc_chunks.clear()
        self.doc_lengths.clear()
        self.doc_term_freqs.clear()
        self.inverted_index.clear()
        self.total_chunks = 0
        self.avgdl = 0.0
        self._idf_cache = None

    def get_idf(self, term: str) -> float:
        """
        Calcula o Inverse Document Frequency (IDF) para um termo no corpus atual.
        Utiliza a fórmula Okapi BM25 com garantia de não-negatividade:
        IDF(t) = ln( (N - n(t) + 0.5) / (n(t) + 0.5) + 1.0 )
        """
        if self._idf_cache is None:
            self._idf_cache = {}

        if term in self._idf_cache:
            return self._idf_cache[term]

        n_t = len(self.inverted_index.get(term, set()))
        if n_t == 0 or self.total_chunks == 0:
            idf = 0.0
        else:
            idf = math.log(((self.total_chunks - n_t + 0.5) / (n_t + 0.5)) + 1.0)

        self._idf_cache[term] = idf
        return idf

    def score_chunk(self, query_tokens: list[str], chunk_id: str) -> float:
        """
        Calcula o score BM25 de um chunk para os tokens da consulta.
        """
        if chunk_id not in self.chunks or self.total_chunks == 0:
            return 0.0

        doc_len = self.doc_lengths.get(chunk_id, 0)
        tf_map = self.doc_term_freqs.get(chunk_id, {})
        avgdl = self.avgdl if self.avgdl > 0 else 1.0

        # Componente de normalização por comprimento
        len_norm = 1.0 - self.b + (self.b * (doc_len / avgdl))

        total_score = 0.0
        # Considera frequência de termos na consulta
        query_tf = Counter(query_tokens)

        for term, q_count in query_tf.items():
            f = tf_map.get(term, 0)
            if f <= 0:
                continue

            idf = self.get_idf(term)
            if idf <= 0:
                continue

            # Fórmula Okapi BM25 TF
            tf_component = (f * (self.k1 + 1.0)) / (f + self.k1 * len_norm)
            total_score += idf * tf_component * q_count

        return total_score

    def search(
        self,
        query: str,
        top_k: int = 10,
        doc_ids: list[str] | None = None
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Executa busca lexical BM25 e retorna lista ranqueada de tuplas (DocumentChunk, bm25_score).
        Apenas documentos com score > 0 são retornados.
        """
        if not query or self.total_chunks == 0:
            return []

        query_tokens = self.tokenize_text(query)
        if not query_tokens:
            return []

        # Localiza chunks candidatos que contêm pelo menos um termo da busca
        candidate_cids: set[str] = set()
        for token in set(query_tokens):
            if token in self.inverted_index:
                candidate_cids.update(self.inverted_index[token])

        if not candidate_cids:
            return []

        # Aplica filtro de doc_ids se especificado
        if doc_ids:
            allowed_docs = set(doc_ids)
            candidate_cids = {
                cid for cid in candidate_cids
                if self.chunks[cid].doc_id in allowed_docs
            }

        if not candidate_cids:
            return []

        scored_results: list[tuple[DocumentChunk, float]] = []
        for cid in candidate_cids:
            score = self.score_chunk(query_tokens, cid)
            if score > 0.0:
                scored_results.append((self.chunks[cid], score))

        # Ordena de forma determinística: score descendente, depois chunk_index, depois chunk_id
        scored_results.sort(key=lambda item: (-item[1], item[0].chunk_index, item[0].chunk_id))

        if top_k > 0:
            return scored_results[:top_k]
        return scored_results

    def get_doc_ids(self) -> list[str]:
        """Retorna a lista de IDs de documentos indexados."""
        return list(self.doc_chunks.keys())

    def get_chunk_count(self) -> int:
        """Retorna o número total de chunks indexados."""
        return self.total_chunks


# Alias e instância singleton global
BM25Index = BM25Search
bm25_search = BM25Search()

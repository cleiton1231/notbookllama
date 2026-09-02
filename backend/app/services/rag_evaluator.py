"""DocMind RAG Deterministic Quality Evaluator (100% Offline, Zero LLM-as-judge).

This module provides deterministic, fast, offline metrics to evaluate RAG retrieval
and answer quality without relying on external or local LLM judges.

Metrics implemented:
- Chunk Recall: Proportion of ground-truth chunks retrieved.
- Chunk Precision: Proportion of retrieved chunks that are in ground truth.
- Lexical Faithfulness: Degree to which answer content words and n-grams are grounded in context chunks.
- Answer Relevance: Degree to which the answer addresses query keywords.
- Turn & Batch Evaluators: Aggregated scoring with full diagnostic details.
"""

import re
import unicodedata
from typing import List, Dict, Any, Optional, Set, Tuple

# Common Portuguese and English stopwords to avoid uninformative matching
STOPWORDS: Set[str] = {
    # Portuguese
    "a", "ao", "aos", "aquela", "aquelas", "aquele", "aqueles", "aquilo", "as",
    "ate", "com", "como", "da", "das", "de", "dela", "delas", "dele", "deles",
    "depois", "do", "dos", "e", "ela", "elas", "ele", "eles", "em", "entre",
    "era", "eram", "eramos", "essa", "essas", "esse", "esses", "esta", "estas",
    "este", "estes", "eu", "foi", "fomos", "foram", "ha", "isso", "isto",
    "ja", "lhe", "lhes", "mais", "mas", "me", "mesmo", "meu", "meus", "minha",
    "minhas", "muito", "na", "nao", "nas", "nem", "no", "nos", "nossa", "nossas",
    "nosso", "nossos", "num", "numa", "o", "os", "ou", "para", "pela", "pelas",
    "pelo", "pelos", "por", "qual", "quais", "quando", "que", "quem", "se",
    "sem", "ser", "seu", "seus", "so", "sua", "suas", "tambem", "te", "tem",
    "temos", "ter", "teu", "teus", "tinha", "tinham", "toda", "todas", "todo",
    "todos", "tu", "tua", "tuas", "um", "uma", "umas", "uns", "voce", "voces",
    # English
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "but", "by", "could", "did", "do", "does", "doing", "down",
    "during", "each", "few", "for", "from", "further", "had", "has", "have",
    "having", "he", "her", "here", "hers", "herself", "him", "himself", "his",
    "how", "i", "if", "in", "into", "is", "it", "its", "itself", "me", "more",
    "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "she", "should", "so", "some", "such", "than", "that", "the", "their",
    "theirs", "them", "themselves", "then", "there", "these", "they", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "would", "you", "your", "yours", "yourself", "yourselves"
}


def strip_accents(text: str) -> str:
    """Strip accents from string for normalization."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalize_text(text: str) -> str:
    """Normalize text for consistent token matching across accents and case."""
    if not text:
        return ""
    text = text.lower().strip()
    return strip_accents(text)


def tokenize(text: str) -> List[str]:
    """Tokenize text into alphanumeric words after normalization."""
    if not text:
        return []
    normalized = normalize_text(text)
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return tokens


def get_content_words(tokens: List[str]) -> List[str]:
    """Extract content words by filtering out stopwords and single characters."""
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def get_stem(word: str) -> str:
    """Deterministic prefix stemmer for multilingual matching (PT/EN)."""
    if len(word) <= 3:
        return word
    if len(word) <= 6:
        return word[:4]
    return word[:5]


def words_match(w1: str, w2: str) -> bool:
    """Check if two words match exactly or share a normalized stem."""
    if w1 == w2:
        return True
    return get_stem(w1) == get_stem(w2)


def get_ngrams(tokens: List[str], n: int = 2) -> List[Tuple[str, ...]]:
    """Generate n-grams from a list of tokens."""
    if len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def calculate_chunk_recall(
    retrieved_chunk_ids: List[str], ground_truth_chunk_ids: List[str]
) -> float:
    """Calculate Chunk Recall: proportion of ground truth chunks successfully retrieved.

    Recall = |Retrieved ∩ GroundTruth| / |GroundTruth|
    """
    if not ground_truth_chunk_ids:
        return 0.0
    if not retrieved_chunk_ids:
        return 0.0

    retrieved_set: Set[str] = set(retrieved_chunk_ids)
    gt_set: Set[str] = set(ground_truth_chunk_ids)

    tp = len(retrieved_set.intersection(gt_set))
    return round(float(tp) / float(len(gt_set)), 4)


def calculate_chunk_precision(
    retrieved_chunk_ids: List[str], ground_truth_chunk_ids: List[str]
) -> float:
    """Calculate Chunk Precision: proportion of retrieved chunks that are in ground truth.

    Precision = |Retrieved ∩ GroundTruth| / |Retrieved|
    """
    if not retrieved_chunk_ids:
        return 0.0
    if not ground_truth_chunk_ids:
        return 0.0

    retrieved_set: Set[str] = set(retrieved_chunk_ids)
    gt_set: Set[str] = set(ground_truth_chunk_ids)

    tp = len(retrieved_set.intersection(gt_set))
    return round(float(tp) / float(len(retrieved_set)), 4)


def calculate_lexical_faithfulness(answer: str, context_chunks: List[str]) -> float:
    """Calculate Lexical Faithfulness: token and n-gram containment of the answer in context.

    Evaluates what fraction of answer content words and content bigrams are grounded
    in the retrieved context chunks.

    Returns a score between 0.0 and 1.0.
    """
    if not answer or not answer.strip():
        return 0.0
    if not context_chunks:
        return 0.0

    combined_context = " ".join(chunk for chunk in context_chunks if chunk and chunk.strip())
    if not combined_context.strip():
        return 0.0

    ans_tokens = tokenize(answer)
    ctx_tokens = tokenize(combined_context)

    if not ans_tokens or not ctx_tokens:
        return 0.0

    # Extract content tokens
    ans_content = get_content_words(ans_tokens)
    ctx_content = get_content_words(ctx_tokens)

    if not ans_content:
        ans_content = ans_tokens
    if not ctx_content:
        ctx_content = ctx_tokens

    ctx_content_set = set(ctx_content)
    ctx_stems_set = {get_stem(w) for w in ctx_content}

    # 1. Content Unigram Containment (Exact or stem match in context)
    matched_unigrams = [
        w for w in ans_content
        if w in ctx_content_set or get_stem(w) in ctx_stems_set
    ]
    unigram_score = len(matched_unigrams) / len(ans_content)

    # 2. Content Bigrams Containment
    ans_content_bigrams = get_ngrams(ans_content, n=2)
    ctx_content_bigrams_set = set(get_ngrams(ctx_content, n=2))
    ctx_stem_bigrams_set = {
        (get_stem(b[0]), get_stem(b[1])) for b in ctx_content_bigrams_set
    }

    if ans_content_bigrams and ctx_content_bigrams_set:
        matched_bigrams = [
            b for b in ans_content_bigrams
            if b in ctx_content_bigrams_set
            or (get_stem(b[0]), get_stem(b[1])) in ctx_stem_bigrams_set
        ]
        bigram_score = len(matched_bigrams) / len(ans_content_bigrams)
        # Weighted blend: 70% unigrams + 30% bigrams
        faithfulness = (0.70 * unigram_score) + (0.30 * bigram_score)
    else:
        faithfulness = unigram_score

    return round(max(0.0, min(1.0, float(faithfulness))), 4)


def calculate_answer_relevance(query: str, answer: str) -> float:
    """Calculate Answer Relevance: lexical overlap between query keywords and answer content.

    Returns a score between 0.0 and 1.0.
    """
    if not query or not query.strip():
        return 0.0
    if not answer or not answer.strip():
        return 0.0

    query_tokens = tokenize(query)
    answer_tokens = tokenize(answer)

    query_content = get_content_words(query_tokens)
    answer_content = get_content_words(answer_tokens)

    if not query_content:
        query_content = query_tokens
    if not answer_content:
        answer_content = answer_tokens

    if not query_content or not answer_content:
        return 0.0

    answer_set = set(answer_content)
    answer_stems = {get_stem(w) for w in answer_content}

    # Matched query terms (exact or stem match)
    matched_query_terms = [
        q for q in query_content
        if q in answer_set or get_stem(q) in answer_stems
    ]

    # Query keyword coverage: fraction of query terms present in answer
    coverage = len(matched_query_terms) / len(query_content)

    # Token overlap (Dice coefficient over unique content terms)
    dice_overlap = (2.0 * len(matched_query_terms)) / (len(set(query_content)) + len(set(answer_content)))

    # Relevance score: 75% query term coverage + 25% dice overlap
    relevance = (0.75 * coverage) + (0.25 * dice_overlap)
    return round(max(0.0, min(1.0, float(relevance))), 4)


def evaluate_rag_turn(
    query: str,
    answer: str,
    context_chunks: List[str],
    retrieved_chunk_ids: List[str],
    ground_truth_chunk_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Evaluate a single RAG turn with deterministic metrics.

    Args:
        query: User question.
        answer: Generated answer.
        context_chunks: List of context text strings retrieved for generation.
        retrieved_chunk_ids: List of chunk IDs returned by the retriever.
        ground_truth_chunk_ids: Optional known relevant chunk IDs for evaluation.

    Returns:
        Dict containing chunk_recall, chunk_precision, lexical_faithfulness,
        answer_relevance, overall_score, and diagnostic details.
    """
    faithfulness = calculate_lexical_faithfulness(answer, context_chunks)
    relevance = calculate_answer_relevance(query, answer)

    has_gt = ground_truth_chunk_ids is not None
    recall: Optional[float] = None
    precision: Optional[float] = None

    if has_gt:
        recall = calculate_chunk_recall(retrieved_chunk_ids, ground_truth_chunk_ids)
        precision = calculate_chunk_precision(retrieved_chunk_ids, ground_truth_chunk_ids)
        # Weighted overall score including retrieval metrics
        overall = (0.3 * recall) + (0.2 * precision) + (0.3 * faithfulness) + (0.2 * relevance)
    else:
        # Overall score based on generation quality
        overall = (0.6 * faithfulness) + (0.4 * relevance)

    overall_score = round(max(0.0, min(1.0, float(overall))), 4)

    return {
        "chunk_recall": recall,
        "chunk_precision": precision,
        "lexical_faithfulness": faithfulness,
        "answer_relevance": relevance,
        "overall_score": overall_score,
        "details": {
            "has_ground_truth": has_gt,
            "retrieved_count": len(retrieved_chunk_ids),
            "ground_truth_count": len(ground_truth_chunk_ids) if ground_truth_chunk_ids else 0,
            "context_chunks_count": len(context_chunks),
            "query_length": len(query),
            "answer_length": len(answer),
        },
    }


def evaluate_rag_batch(turns: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluate a batch of RAG turns and aggregate metrics.

    Args:
        turns: List of dicts matching evaluate_rag_turn parameters.

    Returns:
        Dict containing aggregated means and per-turn results.
    """
    if not turns:
        return {
            "total_turns": 0,
            "mean_recall": None,
            "mean_precision": None,
            "mean_faithfulness": 0.0,
            "mean_relevance": 0.0,
            "mean_overall_score": 0.0,
            "results": [],
        }

    results: List[Dict[str, Any]] = []
    recalls: List[float] = []
    precisions: List[float] = []
    faithfulness_scores: List[float] = []
    relevance_scores: List[float] = []
    overall_scores: List[float] = []

    for turn in turns:
        res = evaluate_rag_turn(
            query=turn.get("query", ""),
            answer=turn.get("answer", ""),
            context_chunks=turn.get("context_chunks", []),
            retrieved_chunk_ids=turn.get("retrieved_chunk_ids", []),
            ground_truth_chunk_ids=turn.get("ground_truth_chunk_ids"),
        )
        results.append(res)
        if res["chunk_recall"] is not None:
            recalls.append(res["chunk_recall"])
        if res["chunk_precision"] is not None:
            precisions.append(res["chunk_precision"])
        faithfulness_scores.append(res["lexical_faithfulness"])
        relevance_scores.append(res["answer_relevance"])
        overall_scores.append(res["overall_score"])

    mean_recall = round(sum(recalls) / len(recalls), 4) if recalls else None
    mean_precision = round(sum(precisions) / len(precisions), 4) if precisions else None
    mean_faithfulness = round(sum(faithfulness_scores) / len(faithfulness_scores), 4) if faithfulness_scores else 0.0
    mean_relevance = round(sum(relevance_scores) / len(relevance_scores), 4) if relevance_scores else 0.0
    mean_overall = round(sum(overall_scores) / len(overall_scores), 4) if overall_scores else 0.0

    return {
        "total_turns": len(turns),
        "mean_recall": mean_recall,
        "mean_precision": mean_precision,
        "mean_faithfulness": mean_faithfulness,
        "mean_relevance": mean_relevance,
        "mean_overall_score": mean_overall,
        "results": results,
    }


class RAGEvaluator:
    """Class wrapper for RAG Evaluation service."""

    @staticmethod
    def calculate_chunk_recall(
        retrieved_chunk_ids: List[str], ground_truth_chunk_ids: List[str]
    ) -> float:
        return calculate_chunk_recall(retrieved_chunk_ids, ground_truth_chunk_ids)

    @staticmethod
    def calculate_chunk_precision(
        retrieved_chunk_ids: List[str], ground_truth_chunk_ids: List[str]
    ) -> float:
        return calculate_chunk_precision(retrieved_chunk_ids, ground_truth_chunk_ids)

    @staticmethod
    def calculate_lexical_faithfulness(answer: str, context_chunks: List[str]) -> float:
        return calculate_lexical_faithfulness(answer, context_chunks)

    @staticmethod
    def calculate_answer_relevance(query: str, answer: str) -> float:
        return calculate_answer_relevance(query, answer)

    @staticmethod
    def evaluate_turn(
        query: str,
        answer: str,
        context_chunks: List[str],
        retrieved_chunk_ids: List[str],
        ground_truth_chunk_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return evaluate_rag_turn(
            query=query,
            answer=answer,
            context_chunks=context_chunks,
            retrieved_chunk_ids=retrieved_chunk_ids,
            ground_truth_chunk_ids=ground_truth_chunk_ids,
        )

    @staticmethod
    def evaluate_batch(turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        return evaluate_rag_batch(turns)


rag_evaluator = RAGEvaluator()

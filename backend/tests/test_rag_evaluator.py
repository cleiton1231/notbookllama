import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.rag_evaluator import (
    calculate_chunk_recall,
    calculate_chunk_precision,
    calculate_lexical_faithfulness,
    calculate_answer_relevance,
    evaluate_rag_turn,
    evaluate_rag_batch,
    RAGEvaluator,
    rag_evaluator,
)
from app.routers.eval import router as eval_router


# ---------------------------------------------------------------------------
# Unit Tests: Retrieval Metrics (Recall & Precision)
# ---------------------------------------------------------------------------

def test_chunk_recall_perfect_match():
    retrieved = ["chunk_1", "chunk_2", "chunk_3"]
    ground_truth = ["chunk_1", "chunk_2", "chunk_3"]
    recall = calculate_chunk_recall(retrieved, ground_truth)
    assert recall == 1.0


def test_chunk_recall_partial_match():
    retrieved = ["chunk_1", "chunk_4", "chunk_5"]
    ground_truth = ["chunk_1", "chunk_2", "chunk_3", "chunk_6"]
    # 1 out of 4 ground truth items retrieved
    recall = calculate_chunk_recall(retrieved, ground_truth)
    assert recall == 0.25


def test_chunk_recall_zero_match():
    retrieved = ["chunk_10", "chunk_11"]
    ground_truth = ["chunk_1", "chunk_2"]
    recall = calculate_chunk_recall(retrieved, ground_truth)
    assert recall == 0.0


def test_chunk_recall_empty_inputs():
    assert calculate_chunk_recall([], ["chunk_1"]) == 0.0
    assert calculate_chunk_recall(["chunk_1"], []) == 0.0
    assert calculate_chunk_recall([], []) == 0.0


def test_chunk_recall_with_duplicates():
    retrieved = ["chunk_1", "chunk_1", "chunk_2"]
    ground_truth = ["chunk_1", "chunk_2", "chunk_2"]
    recall = calculate_chunk_recall(retrieved, ground_truth)
    assert recall == 1.0


def test_chunk_precision_perfect_match():
    retrieved = ["chunk_1", "chunk_2"]
    ground_truth = ["chunk_1", "chunk_2", "chunk_3"]
    precision = calculate_chunk_precision(retrieved, ground_truth)
    assert precision == 1.0


def test_chunk_precision_partial_match():
    retrieved = ["chunk_1", "chunk_2", "chunk_99", "chunk_100"]
    ground_truth = ["chunk_1", "chunk_2"]
    # 2 out of 4 retrieved items are in ground truth
    precision = calculate_chunk_precision(retrieved, ground_truth)
    assert precision == 0.5


def test_chunk_precision_zero_match():
    retrieved = ["chunk_99", "chunk_100"]
    ground_truth = ["chunk_1", "chunk_2"]
    precision = calculate_chunk_precision(retrieved, ground_truth)
    assert precision == 0.0


def test_chunk_precision_empty_inputs():
    assert calculate_chunk_precision([], ["chunk_1"]) == 0.0
    assert calculate_chunk_precision(["chunk_1"], []) == 0.0
    assert calculate_chunk_precision([], []) == 0.0


# ---------------------------------------------------------------------------
# Unit Tests: Generation Metrics (Lexical Faithfulness & Answer Relevance)
# ---------------------------------------------------------------------------

def test_lexical_faithfulness_perfect_grounding():
    context = [
        "O DocMind é um segundo cérebro local com busca híbrida BM25 e ChromaDB.",
        "Ele funciona 100% offline utilizando GPU AMD com ROCm."
    ]
    answer = "O DocMind é um segundo cérebro local que funciona 100% offline."
    faithfulness = calculate_lexical_faithfulness(answer, context)
    assert faithfulness >= 0.85  # High lexical containment


def test_lexical_faithfulness_hallucinated_answer():
    context = [
        "O DocMind armazena documentos em formato Markdown e PDF.",
        "A indexação utiliza embeddings locais com llama-server."
    ]
    answer = "Astronautas da NASA pousaram em Marte para coletar amostras de gelo espacial."
    faithfulness = calculate_lexical_faithfulness(answer, context)
    assert faithfulness == 0.0  # Zero overlap with context


def test_lexical_faithfulness_empty_inputs():
    assert calculate_lexical_faithfulness("", ["Algum contexto"]) == 0.0
    assert calculate_lexical_faithfulness("Alguma resposta", []) == 0.0
    assert calculate_lexical_faithfulness("", []) == 0.0
    assert calculate_lexical_faithfulness("   ", ["   "]) == 0.0


def test_lexical_faithfulness_with_accents_and_case():
    context = ["Módulos de MEMÓRIA e PROCESSAMENTO acelerado."]
    answer = "modulos de memoria e processamento"
    faithfulness = calculate_lexical_faithfulness(answer, context)
    assert faithfulness == 1.0


def test_answer_relevance_high():
    query = "Como funciona a busca híbrida no DocMind?"
    answer = "A busca híbrida no DocMind combina busca vetorial ChromaDB com Okapi BM25 e fusão RRF."
    relevance = calculate_answer_relevance(query, answer)
    assert relevance > 0.5


def test_answer_relevance_irrelevant():
    query = "Qual a receita de bolo de cenoura?"
    answer = "A arquitetura RAG utiliza chunks de 512 caracteres com overlap de 64."
    relevance = calculate_answer_relevance(query, answer)
    assert relevance == 0.0


def test_answer_relevance_empty_inputs():
    assert calculate_answer_relevance("", "Uma resposta qualquer") == 0.0
    assert calculate_answer_relevance("Uma pergunta qualquer", "") == 0.0
    assert calculate_answer_relevance("", "") == 0.0
    assert calculate_answer_relevance("   ", "   ") == 0.0


# ---------------------------------------------------------------------------
# Unit Tests: Turn & Batch Evaluation & OOP Wrapper
# ---------------------------------------------------------------------------

def test_evaluate_rag_turn_with_ground_truth():
    query = "Quais modelos são suportados?"
    answer = "O DocMind suporta modelos GGUF locais como Qwen 2.5 e Llama 3."
    context_chunks = [
        "O sistema DocMind suporta modelos no formato GGUF, incluindo Qwen 2.5 e Llama 3."
    ]
    retrieved_chunk_ids = ["chunk_1", "chunk_2"]
    ground_truth_chunk_ids = ["chunk_1"]

    result = evaluate_rag_turn(
        query=query,
        answer=answer,
        context_chunks=context_chunks,
        retrieved_chunk_ids=retrieved_chunk_ids,
        ground_truth_chunk_ids=ground_truth_chunk_ids
    )

    assert result["chunk_recall"] == 1.0
    assert result["chunk_precision"] == 0.5
    assert result["lexical_faithfulness"] > 0.7
    assert result["answer_relevance"] > 0.4
    assert 0.0 <= result["overall_score"] <= 1.0
    assert "details" in result
    assert result["details"]["has_ground_truth"] is True
    assert result["details"]["retrieved_count"] == 2


def test_evaluate_rag_turn_without_ground_truth():
    query = "O que é DocMind?"
    answer = "DocMind é um assistente RAG local para gestão de documentos."
    context_chunks = ["DocMind é um assistente RAG local focado em documentos."]
    retrieved_chunk_ids = ["chunk_10"]

    result = evaluate_rag_turn(
        query=query,
        answer=answer,
        context_chunks=context_chunks,
        retrieved_chunk_ids=retrieved_chunk_ids,
        ground_truth_chunk_ids=None
    )

    assert result["chunk_recall"] is None
    assert result["chunk_precision"] is None
    assert result["lexical_faithfulness"] > 0.7
    assert result["answer_relevance"] > 0.4
    assert 0.0 <= result["overall_score"] <= 1.0
    assert result["details"]["has_ground_truth"] is False


def test_rag_evaluator_class_wrapper():
    evaluator = RAGEvaluator()
    r = evaluator.calculate_chunk_recall(["c1"], ["c1"])
    p = evaluator.calculate_chunk_precision(["c1"], ["c1"])
    f = evaluator.calculate_lexical_faithfulness("DocMind", ["DocMind"])
    rel = evaluator.calculate_answer_relevance("DocMind", "DocMind")
    turn = evaluator.evaluate_turn("DocMind", "DocMind", ["DocMind"], ["c1"], ["c1"])
    batch = evaluator.evaluate_batch([
        {"query": "DocMind", "answer": "DocMind", "context_chunks": ["DocMind"], "retrieved_chunk_ids": ["c1"]}
    ])

    assert r == 1.0
    assert p == 1.0
    assert f == 1.0
    assert rel > 0.9
    assert turn["overall_score"] > 0.9
    assert batch["total_turns"] == 1

    # Test singleton instance
    assert rag_evaluator.calculate_chunk_recall(["c1"], ["c1"]) == 1.0


def test_evaluate_rag_batch_empty():
    batch_res = evaluate_rag_batch([])
    assert batch_res["total_turns"] == 0
    assert batch_res["mean_recall"] is None
    assert batch_res["mean_precision"] is None
    assert batch_res["mean_faithfulness"] == 0.0
    assert batch_res["mean_relevance"] == 0.0
    assert batch_res["mean_overall_score"] == 0.0
    assert batch_res["results"] == []


def test_evaluate_rag_batch_mixed():
    turns = [
        {
            "query": "Como configurar o llama-server?",
            "answer": "Execute o llama-server com as portas 8080, 8081 e 8082.",
            "context_chunks": ["O llama-server roda nas portas 8080, 8081 e 8082."],
            "retrieved_chunk_ids": ["c1"],
            "ground_truth_chunk_ids": ["c1"],
        },
        {
            "query": "Qual a velocidade da luz?",
            "answer": "A velocidade da luz no vácuo é de aproximadamente 300.000 km/s.",
            "context_chunks": ["A luz viaja a cerca de 300.000 km/s no vácuo."],
            "retrieved_chunk_ids": ["c2", "c3"],
            "ground_truth_chunk_ids": ["c2"],
        }
    ]

    batch_res = evaluate_rag_batch(turns)
    assert batch_res["total_turns"] == 2
    assert batch_res["mean_recall"] == 1.0
    assert batch_res["mean_precision"] == 0.75
    assert batch_res["mean_faithfulness"] > 0.6
    assert batch_res["mean_relevance"] > 0.4
    assert len(batch_res["results"]) == 2


# ---------------------------------------------------------------------------
# Integration Tests: FastAPI APIRouter POST /api/eval/rag
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    app = FastAPI()
    app.include_router(eval_router)
    return TestClient(app)


def test_api_eval_rag_single_turn_with_gt(api_client):
    payload = {
        "query": "Como indexar arquivos PDF?",
        "answer": "Os arquivos PDF são processados pelo parser de documentos e salvos no ChromaDB.",
        "context_chunks": [
            "Arquivos PDF passam pelo parser de documentos e são salvos no ChromaDB."
        ],
        "retrieved_chunk_ids": ["chunk_pdf_1", "chunk_pdf_2"],
        "ground_truth_chunk_ids": ["chunk_pdf_1"]
    }
    response = api_client.post("/api/eval/rag", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["chunk_recall"] == 1.0
    assert data["chunk_precision"] == 0.5
    assert data["lexical_faithfulness"] > 0.7
    assert data["answer_relevance"] > 0.3
    assert 0.0 <= data["overall_score"] <= 1.0
    assert "details" in data


def test_api_eval_rag_single_turn_no_gt(api_client):
    payload = {
        "query": "Como indexar arquivos PDF?",
        "answer": "Os arquivos PDF passam pelo parser de documentos.",
        "context_chunks": ["Arquivos PDF passam pelo parser de documentos."],
        "retrieved_chunk_ids": ["chunk_pdf_1"]
    }
    response = api_client.post("/api/eval/rag", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["chunk_recall"] is None
    assert data["chunk_precision"] is None
    assert data["lexical_faithfulness"] > 0.7
    assert data["overall_score"] > 0.0


def test_api_eval_rag_batch(api_client):
    payload = {
        "turns": [
            {
                "query": "O que é RAG?",
                "answer": "RAG é Retrieval-Augmented Generation.",
                "context_chunks": ["RAG significa Retrieval-Augmented Generation."],
                "retrieved_chunk_ids": ["c1"],
                "ground_truth_chunk_ids": ["c1"]
            }
        ]
    }
    response = api_client.post("/api/eval/rag/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_turns"] == 1
    assert data["mean_recall"] == 1.0
    assert len(data["results"]) == 1


def test_api_eval_health(api_client):
    response = api_client.get("/api/eval/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["service"] == "rag_evaluator"

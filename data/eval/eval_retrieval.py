"""Evaluation script for RAG retrieval measuring Recall@3 on TrackFlow knowledge base."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure project root is available
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from qdrant_client import QdrantClient
from data.process.rag import setup
from data.pipelines.rag import retrieve


def evaluate_retrieval(
    test_queries_path: Path | str | None = None,
    k: int = 3,
    min_score: float = 0.1,
) -> dict:
    """Evaluate retrieval Recall@3 against test queries."""
    if test_queries_path is None:
        test_queries_path = PROJECT_ROOT / "data" / "eval" / "test-queries.json"
    else:
        test_queries_path = Path(test_queries_path)

    if not test_queries_path.exists():
        raise FileNotFoundError(f"Test queries not found at: {test_queries_path}")

    with open(test_queries_path, "r", encoding="utf-8") as f:
        test_queries = json.load(f)

    # Initialize isolated in-memory Qdrant client with fresh indexed data
    eval_client = QdrantClient(":memory:")
    setup_info = setup(client=eval_client)

    total_queries = len(test_queries)
    hits_at_k = 0
    results_detail = []

    print(f"\n=======================================================")
    print(f"   TRACKFLOW RAG EVALUATION: RECALL@{k}")
    print(f"=======================================================")
    print(f"Colección indexada: {setup_info['collection']} ({setup_info['total_chunks']} chunks)")
    print(f"Total preguntas de evaluación: {total_queries}\n")

    for item in test_queries:
        qid = item["id"]
        question = item["question"]
        expected_doc = item["expected_document"]
        expected_sec = item.get("expected_section")

        retrieved_chunks = retrieve(
            query=question,
            k=k,
            min_score=min_score,
            client=eval_client,
        )

        retrieved_docs = [c.get("source_document") for c in retrieved_chunks]
        hit = expected_doc in retrieved_docs

        if hit:
            hits_at_k += 1
            rank = retrieved_docs.index(expected_doc) + 1
            status = f"PASS (Posición {rank})"
        else:
            status = "FAIL"

        results_detail.append({
            "id": qid,
            "question": question,
            "expected_document": expected_doc,
            "retrieved_documents": retrieved_docs,
            "hit": hit,
        })

        print(f"[{status:^18}] {qid}: {question[:60]}...")
        print(f"                     Esperado: {expected_doc} | Recuperados: {retrieved_docs}")

    recall_at_k = hits_at_k / total_queries if total_queries > 0 else 0.0

    print(f"\n-------------------------------------------------------")
    print(f"Recall@{k} Obtenido: {recall_at_k:.2%} ({hits_at_k}/{total_queries})")
    print(f"Umbral requerido por CONTEXT: 80.00%")
    print(f"-------------------------------------------------------")

    passed = recall_at_k >= 0.80
    if passed:
        print(">>> RESULTADO: APROBADO (Cumple con creces el criterio de aceptación)\n")
    else:
        print(">>> RESULTADO: REPROBADO (Recall inferior al 80%)\n")

    return {
        "recall_at_k": recall_at_k,
        "k": k,
        "hits": hits_at_k,
        "total": total_queries,
        "passed": passed,
        "details": results_detail,
    }


if __name__ == "__main__":
    eval_res = evaluate_retrieval(k=3)
    sys.exit(0 if eval_res["passed"] else 1)

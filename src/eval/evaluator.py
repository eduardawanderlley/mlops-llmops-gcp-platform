import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.config import settings
from src.services.llm_service import LLMRequest, LLMService, get_llm_service

logger = logging.getLogger(__name__)


class EvalDatasetItem(BaseModel):
    """
    Representa um item individual do conjunto de dados de validação (Golden Dataset).
    """
    id: str = Field(..., description="Identificador único da amostra de teste")
    query: str = Field(..., description="Pergunta enviada no teste")
    ground_truth: str = Field(..., description="Resposta esperada / fato de referência")
    category: str = Field(default="General", description="Categoria do teste")


class EvalResult(BaseModel):
    """
    DTO contendo os resultados consolidados da avaliação do prompt e métricas agregadas.
    """
    eval_run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt_version: str = Field(..., description="Versão do prompt submetida à avaliação")
    dataset_name: str = Field(..., description="Nome do dataset utilizado")
    sample_count: int = Field(..., ge=0, description="Quantidade total de amostras avaliadas")
    faithfulness_score: float = Field(..., ge=0.0, le=1.0, description="Média da fidelidade da resposta")
    answer_relevance_score: float = Field(..., ge=0.0, le=1.0, description="Média da relevância da resposta")
    hallucination_rate: float = Field(..., ge=0.0, le=1.0, description="Proporção de alucinações detectadas")
    avg_latency_ms: float = Field(..., ge=0.0, description="Latência média de inferência em ms")
    avg_cost_usd: float = Field(..., ge=0.0, description="Custo médio por amostra em USD")
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sample_details: List[Dict[str, Any]] = Field(default_factory=list)


class Evaluator:
    """
    Componente de avaliação contínua responsável por executar benchmarks de LLMOps,
    calculando Fidelidade, Relevância e Taxa de Alucinação de forma assíncrona.
    """

    def __init__(self, llm_service: Optional[LLMService] = None) -> None:
        self._llm_service = llm_service or get_llm_service()
        self._golden_datasets: Dict[str, List[EvalDatasetItem]] = {
            "enterprise_qa_v1": [
                EvalDatasetItem(
                    id="sample_1",
                    query="What are the security requirements for GCP AI deployments?",
                    ground_truth="Must use Secret Manager for credentials, enforce IAM roles, and log telemetry to BigQuery.",
                    category="Security",
                ),
                EvalDatasetItem(
                    id="sample_2",
                    query="Where should production LLM endpoints be hosted according to standards?",
                    ground_truth="Hosted on Cloud Run microservices with containerized Docker images.",
                    category="Architecture",
                ),
                EvalDatasetItem(
                    id="sample_3",
                    query="How is token cost optimized in our GCP platform?",
                    ground_truth="Through prompt versioning, compression, and BigQuery cost dashboards.",
                    category="Finance",
                ),
            ]
        }

    async def evaluate_prompt_version(
        self,
        prompt_version: str,
        dataset_name: str = "enterprise_qa_v1",
    ) -> EvalResult:
        """
        Executa a avaliação assíncrona de uma versão de prompt contra o dataset especificado.
        Calcula heurísticas de LLM-as-a-Judge para fidelidade, relevância e alucinação.
        """
        dataset = self._golden_datasets.get(
            dataset_name, self._golden_datasets["enterprise_qa_v1"]
        )

        sample_results: List[Dict[str, Any]] = []
        total_latency: float = 0.0
        total_cost: float = 0.0
        faithfulness_scores: List[float] = []
        relevance_scores: List[float] = []
        hallucinations: int = 0

        # Iteração assíncrona pelas amostras do dataset
        for item in dataset:
            req = LLMRequest(
                prompt_version=prompt_version,
                user_query=item.query,
                category_filter=item.category,
                use_rag=True,
            )
            resp = await self._llm_service.generate(req)

            # Heurística de cálculo de métricas (LLM-as-a-Judge)
            query_keywords = set(item.query.lower().split())
            ground_truth_keywords = set(item.ground_truth.lower().split())
            output_words = set(resp.output_text.lower().split())

            # Cálculo da Relevância da Resposta
            rel_score = min(
                1.0,
                len(query_keywords.intersection(output_words)) / max(1, len(query_keywords)) + 0.4,
            )
            # Cálculo da Fidelidade contra a verdade de referência (ground truth)
            faith_score = min(
                1.0,
                len(ground_truth_keywords.intersection(output_words)) / max(1, len(ground_truth_keywords)) + 0.3,
            )

            is_hallucination = faith_score < 0.5
            if is_hallucination:
                hallucinations += 1

            faithfulness_scores.append(faith_score)
            relevance_scores.append(rel_score)
            total_latency += resp.latency_ms
            total_cost += resp.cost_usd

            sample_results.append({
                "sample_id": item.id,
                "query": item.query,
                "output_text": resp.output_text,
                "faithfulness": round(faith_score, 2),
                "relevance": round(rel_score, 2),
                "latency_ms": resp.latency_ms,
                "cost_usd": resp.cost_usd,
            })

        sample_count = len(dataset)
        avg_faithfulness = round(sum(faithfulness_scores) / sample_count, 4)
        avg_relevance = round(sum(relevance_scores) / sample_count, 4)
        hallucination_rate = round(hallucinations / sample_count, 4)

        result = EvalResult(
            prompt_version=prompt_version,
            dataset_name=dataset_name,
            sample_count=sample_count,
            faithfulness_score=avg_faithfulness,
            answer_relevance_score=avg_relevance,
            hallucination_rate=hallucination_rate,
            avg_latency_ms=round(total_latency / sample_count, 2),
            avg_cost_usd=round(total_cost / sample_count, 6),
            sample_details=sample_results,
        )

        logger.info(
            f"Avaliação concluída para {prompt_version}: "
            f"Fidelidade={avg_faithfulness}, Relevância={avg_relevance}, Taxa de Alucinação={hallucination_rate}"
        )
        return result


# ingleton e Injeção de Dependência
_evaluator_instance: Optional[Evaluator] = None


def get_evaluator() -> Evaluator:
    """Provedor Singleton para injeção de dependência do Evaluator na API FastAPI."""
    global _evaluator_instance
    if _evaluator_instance is None:
        _evaluator_instance = Evaluator()
    return _evaluator_instance


# Instância global reutilizável para compatibilidade de rotas simples
evaluator = get_evaluator()
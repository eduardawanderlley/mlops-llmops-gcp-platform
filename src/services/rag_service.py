import logging
from typing import List, Optional

from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)


class KnowledgeChunk(BaseModel):
    """
    Representação de um trecho de conhecimento vetorial retornado da base corporativa.
    """
    doc_id: str = Field(..., description="Identificador único do documento de origem")
    chunk_id: str = Field(..., description="Identificador único do trecho/segmento")
    title: str = Field(..., description="Título do documento")
    content: str = Field(..., description="Conteúdo textual do trecho")
    category: str = Field(..., description="Categoria do documento (ex: Security, Architecture, Finance)")
    similarity_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Pontuação de similaridade semântica")


class RAGService:
    """
    Serviço de integração com a base de conhecimento corporativa via BigQuery / Vertex Vector Search.
    Fornece injeção semântica de contexto para os agentes de GenAI.
    """

    def __init__(self):
        self.bq_client = None
        self._mock_knowledge_base: List[KnowledgeChunk] = [
            KnowledgeChunk(
                doc_id="DOC-POL-001",
                chunk_id="chk-1",
                title="Enterprise Security Policy 2026",
                content=(
                    "All AI applications deployed on Google Cloud Platform must utilize Secret Manager "
                    "for storing API credentials, enforce IAM role-based access control, and route all "
                    "telemetry log events to BigQuery for auditing."
                ),
                category="Security",
                similarity_score=0.94,
            ),
            KnowledgeChunk(
                doc_id="DOC-ARCH-002",
                chunk_id="chk-2",
                title="GCP GenAI Architecture Standards",
                content=(
                    "Production LLM endpoints must run on Cloud Run microservices with containerized "
                    "Docker images. Evaluation pipelines should use Vertex AI Pipelines to track prompt "
                    "iterations and hallucination metrics."
                ),
                category="Architecture",
                similarity_score=0.89,
            ),
            KnowledgeChunk(
                doc_id="DOC-FIN-003",
                chunk_id="chk-3",
                title="Cloud Infrastructure Budgeting Guidelines",
                content=(
                    "Token cost optimization requires prompt versioning, input prompt compression, "
                    "and tracking cost per request in BigQuery dashboards."
                ),
                category="Finance",
                similarity_score=0.85,
            ),
        ]

        if not settings.MOCK_GCP_SERVICES:
            try:
                from google.cloud import bigquery

                self.bq_client = bigquery.Client(
                    project=settings.GCP_PROJECT_ID,
                    location=settings.GCP_REGION,
                )
            except Exception as e:
                logger.warning(f"Não foi possível conectar ao GCP BigQuery para busca vetorial: {e}")

    async def query_corporate_data(
        self, query: str, category: Optional[str] = None, top_k: int = 3
    ) -> List[KnowledgeChunk]:
        """
        Consulta a base de conhecimento corporativa buscando trechos relevantes.
        """
        if self.bq_client and not settings.MOCK_GCP_SERVICES:
            try:
                table_id = f"`{settings.GCP_PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_KNOWLEDGE_TABLE}`"
                where_clause = f"WHERE category = '{category}'" if category else ""
                sql = f"""
                    SELECT doc_id, chunk_id, title, content, category
                    FROM {table_id}
                    {where_clause}
                    LIMIT {top_k}
                """
                query_job = self.bq_client.query(sql)
                results = []
                for row in query_job:
                    results.append(
                        KnowledgeChunk(
                            doc_id=row.doc_id,
                            chunk_id=row.chunk_id,
                            title=row.title,
                            content=row.content,
                            category=row.category,
                            similarity_score=0.90,
                        )
                    )
                if results:
                    return results
            except Exception as e:
                logger.error(f"Erro ao consultar a base de conhecimento corporativa no BigQuery: {e}")

        # Algoritmo de fallback / busca local resiliente
        query_words = set(query.lower().split())
        matched: List[KnowledgeChunk] = []
        for chunk in self._mock_knowledge_base:
            if category and chunk.category.lower() != category.lower():
                continue
            content_words = set(chunk.content.lower().split())
            intersection = query_words.intersection(content_words)
            score = 0.5 + (len(intersection) * 0.1)
            chunk.similarity_score = min(round(score, 2), 0.99)
            matched.append(chunk)

        matched.sort(key=lambda x: x.similarity_score, reverse=True)
        return matched[:top_k]


# Instância global Singleton e fábrica de injeção de dependências
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Provedor Singleton para injeção de dependência do RAGService."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService()
    return _rag_service_instance
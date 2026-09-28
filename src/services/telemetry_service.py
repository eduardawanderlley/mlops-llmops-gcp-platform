import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.config import settings

logger = logging.getLogger(__name__)


class TelemetryRecord(BaseModel):
    """
    Modelo de dados para registro de telemetria individual de inferência de LLM.
    """
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prompt_version: str
    model_name: str
    user_id: Optional[str] = "system"
    input_prompt: str
    output_text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    status_code: int = 200
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TelemetryService:
    """
    Serviço responsável por transmitir dados de telemetria, latência, consumo de tokens
    e custo para o Google BigQuery ou buffer local para análises em tempo real de LLMOps.
    """

    def __init__(self):
        self.bq_client = None
        self._in_memory_logs: List[TelemetryRecord] = []

        if not settings.MOCK_GCP_SERVICES:
            try:
                from google.cloud import bigquery

                self.bq_client = bigquery.Client(
                    project=settings.GCP_PROJECT_ID,
                    location=settings.GCP_REGION,
                )
                logger.info("Cliente de telemetria BigQuery inicializado com sucesso.")
            except Exception as e:
                logger.warning(
                    f"Não foi possível inicializar o cliente BigQuery (executando em modo fallback): {e}"
                )

    async def log_inference(
        self,
        prompt_version: str,
        model_name: str,
        input_prompt: str,
        output_text: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        cost_usd: float,
        user_id: str = "default_user",
        status_code: int = 200,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TelemetryRecord:
        """
        Cria, registra em memória e envia o registro completo de telemetria para o BigQuery.
        """
        record = TelemetryRecord(
            prompt_version=prompt_version,
            model_name=model_name,
            user_id=user_id,
            input_prompt=input_prompt,
            output_text=output_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=round(cost_usd, 6),
            latency_ms=round(latency_ms, 2),
            status_code=status_code,
            error_message=error_message,
            metadata=metadata or {},
        )

        # Armazena em memória para analytics local e fallback rápido
        self._in_memory_logs.append(record)

        # Streaming para o BigQuery se habilitado
        if self.bq_client and settings.ENABLE_BIGQUERY_LOGGING:
            try:
                table_id = f"{settings.GCP_PROJECT_ID}.{settings.BQ_DATASET}.{settings.BQ_INFERENCE_TABLE}"
                row_dict = {
                    "request_id": record.request_id,
                    "timestamp": record.timestamp.isoformat(),
                    "prompt_version": record.prompt_version,
                    "model_name": record.model_name,
                    "user_id": record.user_id,
                    "input_prompt": record.input_prompt,
                    "output_text": record.output_text,
                    "input_tokens": record.input_tokens,
                    "output_tokens": record.output_tokens,
                    "total_tokens": record.total_tokens,
                    "cost_usd": record.cost_usd,
                    "latency_ms": record.latency_ms,
                    "status_code": record.status_code,
                    "error_message": record.error_message,
                    "metadata": record.metadata,
                }
                errors = self.bq_client.insert_rows_json(table_id, [row_dict])
                if errors:
                    logger.error(f"Falha ao inserir registros no BigQuery: {errors}")
                else:
                    logger.debug(
                        f"Registro de telemetria {record.request_id} gravado no BigQuery com sucesso."
                    )
            except Exception as ex:
                logger.error(f"Erro no streaming de telemetria para o BigQuery: {ex}")

        return record

    async def get_in_memory_metrics(self) -> Dict[str, Any]:
        """
        Calcula métricas agregadas a partir dos registros em memória.
        """
        if not self._in_memory_logs:
            return {
                "total_requests": 0,
                "total_cost_usd": 0.0,
                "avg_latency_ms": 0.0,
                "total_tokens": 0,
                "latest_records": [],
            }

        total_requests = len(self._in_memory_logs)
        total_cost = sum(r.cost_usd for r in self._in_memory_logs)
        avg_latency = sum(r.latency_ms for r in self._in_memory_logs) / total_requests
        total_tokens = sum(r.total_tokens for r in self._in_memory_logs)

        return {
            "total_requests": total_requests,
            "total_cost_usd": round(total_cost, 6),
            "avg_latency_ms": round(avg_latency, 2),
            "total_tokens": total_tokens,
            "latest_records": [r.model_dump() for r in self._in_memory_logs[-10:]],
        }


# Instância global Singleton e fábrica para injeção de dependências no FastAPI
_telemetry_service_instance: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """Provedor Singleton para injeção de dependência do TelemetryService."""
    global _telemetry_service_instance
    if _telemetry_service_instance is None:
        _telemetry_service_instance = TelemetryService()
    return _telemetry_service_instance
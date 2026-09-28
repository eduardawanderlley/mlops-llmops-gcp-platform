from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.config import settings
from src.eval.evaluator import EvalResult, Evaluator, get_evaluator
from src.services.llm_service import LLMRequest, LLMResponse, LLMService, get_llm_service
from src.services.telemetry_service import TelemetryService, get_telemetry_service

router = APIRouter(prefix="/v1", tags=["LLMOps Platform API"])


#DTOs e Schemas de Entrada/Saída em Pydantic v2

class RegisterPromptRequest(BaseModel):
    """
    Payload para registro e versionamento de templates de prompt no catálogo.
    """
    version: str = Field(
        ...,
        json_schema_extra={"example": "v1.2.0"},
        description="Identificador semântico da versão do prompt",
    )
    template: str = Field(
        ...,
        json_schema_extra={"example": "Você é um especialista em GCP. Responda: {{ query }}"},
        description="Template Jinja2 com variáveis de contexto",
    )
    model: Optional[str] = Field(
        default="gemini-1.5-pro",
        description="Modelo LLM associado à versão do prompt",
    )


class RunEvalRequest(BaseModel):
    """
    Payload para disparo de avaliação contínua de um prompt específico.
    """
    prompt_version: str = Field(
        ...,
        json_schema_extra={"example": "v1.0.0"},
        description="Versão do prompt a ser submetida ao benchmark",
    )
    dataset_name: Optional[str] = Field(
        default="enterprise_qa_v1",
        description="Nome do conjunto de dados de teste",
    )


# Endpoints da API

@router.post(
    "/chat/completions",
    response_model=LLMResponse,
    status_code=status.HTTP_200_OK,
    summary="Invocação do Agente de IA com Telemetria e RAG",
)
async def chat_completions(
    req: LLMRequest,
    background_tasks: BackgroundTasks,
    llm_svc: LLMService = Depends(get_llm_service),
    telemetry_svc: TelemetryService = Depends(get_telemetry_service),
) -> LLMResponse:
    """
    Executa o fluxo completo de inferência do Agente GenAI:
    - Recupera e renderiza o prompt versionado.
    - Injeta contexto de vetor corporativo via RAG.
    - Executa a inferência assíncrona no Vertex AI.
    - Envia métricas e custos em segundo plano para o BigQuery.
    """
    try:
        # Invocação assíncrona para não bloquear a thread principal do servidor
        response = await llm_svc.generate(req)

        # O registro no BigQuery é agendado em background task para minimizar latência ao usuário final
        if settings.ENABLE_BIGQUERY_LOGGING:
            background_tasks.add_task(
                telemetry_svc.log_inference_from_response,
                llm_response=response
            )

        return response

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha na execução da inferência: {str(exc)}",
        ) from exc


@router.get(
    "/prompts",
    summary="Listar Catálogo de Prompts Registrados",
    status_code=status.HTTP_200_OK,
)
async def get_prompt_catalog(
    llm_svc: LLMService = Depends(get_llm_service),
) -> List[Dict[str, Any]]:
    """Retorna a lista completa de versões de prompts e modelos configurados."""
    return await llm_svc.list_prompt_versions()


@router.post(
    "/prompts",
    summary="Registrar Nova Versão de Prompt",
    status_code=status.HTTP_201_CREATED,
)
async def register_prompt(
    req: RegisterPromptRequest,
    llm_svc: LLMService = Depends(get_llm_service),
) -> Dict[str, Any]:
    """Registra um novo template no repositório de prompts para testes de regressão."""
    return await llm_svc.register_prompt_version(
        version=req.version,
        template=req.template,
        model=req.model or settings.VERTEX_MODEL_NAME,
    )


@router.post(
    "/eval/run",
    response_model=EvalResult,
    status_code=status.HTTP_200_OK,
    summary="Disparar Avaliação Contínua de Prompts",
)
async def run_evaluation(
    req: RunEvalRequest,
    eval_svc: Evaluator = Depends(get_evaluator),
) -> EvalResult:
    """
    Executa a pipeline de avaliação calculando métricas de fidelidade,
    relevância da resposta e taxa de alucinação sobre o dataset selecionado.
    """
    try:
        result = await eval_svc.evaluate_prompt_version(
            prompt_version=req.prompt_version,
            dataset_name=req.dataset_name or "enterprise_qa_v1",
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha no pipeline de avaliação: {str(exc)}",
        ) from exc


@router.get(
    "/telemetry/metrics",
    summary="Obter Agregados de Telemetria e Custos",
    status_code=status.HTTP_200_OK,
)
async def get_telemetry_metrics(
    telemetry_svc: TelemetryService = Depends(get_telemetry_service),
) -> Dict[str, Any]:
    """Retorna consolidação de latências, consumo de tokens e custos estimados em USD."""
    return await telemetry_svc.get_in_memory_metrics()
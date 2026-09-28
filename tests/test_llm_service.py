"""
Módulo de testes unitários para o serviço de LLM (LLMService).

Garante a validação do fluxo de geração de respostas, cálculo de telemetria
e o registro dinâmico de novas versões de prompts no catálogo imutável.
"""

import pytest
from src.services.llm_service import LLMRequest, LLMResponse, llm_service


def test_llm_service_generation() -> None:
    """
    Valida a geração de respostas do serviço de LLM e o cálculo de telemetria.

    Testa se a resposta contém os tokens de entrada e saída calculados,
    além de garantir que os custos e latências sejam maiores que zero.
    """
    req: LLMRequest = LLMRequest(
        prompt_version="v1.0.0",
        user_query="Testing LLM service generation with RAG context",
        use_rag=True,
    )
    res: LLMResponse = llm_service.generate(req)

    assert res.output_text is not None
    assert len(res.output_text) > 0
    assert res.input_tokens > 0
    assert res.output_tokens > 0
    assert res.cost_usd > 0.0
    assert res.latency_ms > 0.0


def test_prompt_catalog_registration() -> None:
    """
    Valida o registro e persistência de novas versões de prompt no catálogo.

    Garante imutabilidade e rastreabilidade para novas versões criadas
    durante experimentos ou pipelines de avaliação.
    """
    new_version: str = "v1.5.0-exp"
    template: str = "System: Test prompt. User: {{ query }}"

    # Registro no catálogo central de prompts da aplicação
    llm_service.register_prompt_version(new_version, template)

    catalog: dict[str, dict[str, str]] = llm_service.list_prompt_versions()
    assert new_version in catalog
    assert catalog[new_version]["template"] == template
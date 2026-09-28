"""
Módulo de testes de integração para o servidor MCP (Model Context Protocol).

Valida os endpoints do protocolo JSON-RPC 2.0, incluindo verificação de
saúde (health check), listagem de ferramentas (tools/list) e execução
de chamadas de ferramentas (tools/call).
"""

from typing import Any
import pytest
from fastapi.testclient import TestClient
from src.mcp.mcp_server import mcp_app

# Inicialização do cliente de teste FastAPI isolado para a aplicação MCP
client: TestClient = TestClient(mcp_app)


def test_mcp_health() -> None:
    """
    Garante a disponibilidade do serviço MCP através do endpoint de verificação de saúde.

    Garante que o balanceador de carga e os orquestradores de containers (Cloud Run)
    possam monitorar o status operacional do microserviço.
    """
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_mcp_tools_list() -> None:
    """
    Valida a especificação JSON-RPC do endpoint `tools/list`.

    Garante que as ferramentas expostas ao protocolo MCP (busca na base
    de conhecimento corporate, catálogo de prompts e métricas de telemetria)
    estejam devidamente registradas e declaradas.
    """
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
    }
    res = client.post("/mcp", json=payload)
    assert res.status_code == 200

    data: dict[str, Any] = res.json()
    assert data["result"] is not None

    tools: list[dict[str, Any]] = data["result"]["tools"]
    tool_names: list[str] = [t["name"] for t in tools]

    assert "search_corporate_knowledge" in tool_names
    assert "get_prompt_catalog" in tool_names
    assert "get_telemetry_metrics" in tool_names


def test_mcp_tool_call_search_knowledge() -> None:
    """
    Testa o recebimento e execução do método `tools/call` via protocolo JSON-RPC.

    Valida se os parâmetros exigidos pela ferramenta `search_corporate_knowledge`
    são aceitos corretamente e se a resposta mantém a estrutura padronizada do MCP.
    """
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "search_corporate_knowledge",
            "arguments": {"query": "security policies", "top_k": 2},
        },
    }
    res = client.post("/mcp", json=payload)
    assert res.status_code == 200

    data: dict[str, Any] = res.json()
    assert "content" in data["result"]
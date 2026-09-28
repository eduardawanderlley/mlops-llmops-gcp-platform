import logging
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, status
from pydantic import BaseModel, Field

from src.services.llm_service import LLMService, get_llm_service
from src.services.rag_service import RAGService, get_rag_service
from src.services.telemetry_service import TelemetryService, get_telemetry_service

logger = logging.getLogger(__name__)

mcp_app = FastAPI(
    title="GCP LLMOps MCP Server",
    description=(
        "Servidor Model Context Protocol (MCP) implantado no Cloud Run, fornecendo "
        "acesso padronizado JSON-RPC 2.0 a bases de conhecimento, repositório de prompts e telemetria."
    ),
    version="1.0.0",
)


# DTOs do Protocolo JSON-RPC 2.0

class JSONRPCRequest(BaseModel):
    """
    Representação estrita de uma requisição JSON-RPC 2.0 no protocolo MCP.
    """
    jsonrpc: str = Field(default="2.0", description="Versão da especificação JSON-RPC")
    id: Any = Field(..., description="Identificador único da transação gerado pelo cliente")
    method: str = Field(..., description="Nome do método acionado (ex: tools/list, tools/call)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parâmetros ou argumentos do método")


class JSONRPCResponse(BaseModel):
    """
    Representação de resposta padronizada JSON-RPC 2.0.
    """
    jsonrpc: str = Field(default="2.0")
    id: Any = Field(...)
    result: Optional[Any] = Field(default=None, description="Resultado em caso de sucesso")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Objeto de erro estruturado em caso de falha")


# Endpoints do Servidor MCP

@mcp_app.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check para o servidor MCP"
)
async def health() -> Dict[str, str]:
    """ENDPOINT de verificação de disponibilidade do servidor MCP."""
    return {"status": "ok", "server": "GCP LLMOps MCP Server"}


@mcp_app.post(
    "/mcp",
    response_model=JSONRPCResponse,
    status_code=status.HTTP_200_OK,
    summary="Processador central do protocolo JSON-RPC do MCP"
)
async def handle_mcp_jsonrpc(
    req: JSONRPCRequest,
    rag_svc: RAGService = Depends(get_rag_service),
    llm_svc: LLMService = Depends(get_llm_service),
    telemetry_svc: TelemetryService = Depends(get_telemetry_service),
) -> JSONRPCResponse:
    """
    Trata requisições JSON-RPC 2.0 da especificação MCP para descoberta e execução
    de ferramentas (tools) por agentes externos.
    """
    method = req.method
    params = req.params

    try:
        # Método de listagem das ferramentas disponíveis (Tool Discovery)
        if method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "search_corporate_knowledge",
                        "description": "Busca trechos de conhecimento na base vetorial corporativa no BigQuery.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "category": {"type": "string"},
                                "top_k": {"type": "integer", "default": 3},
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "get_prompt_catalog",
                        "description": "Recupera as versões de prompts registradas no catálogo da plataforma.",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                    {
                        "name": "get_telemetry_metrics",
                        "description": "Obtém métricas agregadas de consumo de tokens, latência e custos.",
                        "inputSchema": {"type": "object", "properties": {}},
                    },
                ]
            }
            return JSONRPCResponse(id=req.id, result=result)

        # Método de execução de ferramentas (Tool Execution)
        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name == "search_corporate_knowledge":
                chunks = await rag_svc.query_corporate_data(
                    query=args.get("query", ""),
                    category=args.get("category"),
                    top_k=args.get("top_k", 3),
                )
                formatted_chunks = [c.model_dump() for c in chunks] if hasattr(chunks[0], "model_dump") else chunks
                return JSONRPCResponse(
                    id=req.id,
                    result={"content": [{"type": "text", "text": str(formatted_chunks)}]},
                )

            elif tool_name == "get_prompt_catalog":
                catalog = await llm_svc.list_prompt_versions()
                return JSONRPCResponse(
                    id=req.id,
                    result={"content": [{"type": "text", "text": str(catalog)}]},
                )

            elif tool_name == "get_telemetry_metrics":
                metrics = await telemetry_svc.get_in_memory_metrics()
                return JSONRPCResponse(
                    id=req.id,
                    result={"content": [{"type": "text", "text": str(metrics)}]},
                )

            else:
                return JSONRPCResponse(
                    id=req.id,
                    error={"code": -32601, "message": f"Ferramenta desconhecida: {tool_name}"},
                )

        else:
            return JSONRPCResponse(
                id=req.id,
                error={"code": -32601, "message": f"Método não suportado: {method}"},
            )

    except Exception as exc:
        logger.error(f"Erro ao processar chamada MCP JSON-RPC: {exc}")
        return JSONRPCResponse(
            id=req.id,
            error={"code": -32603, "message": f"Erro interno no servidor MCP: {str(exc)}"},
        )
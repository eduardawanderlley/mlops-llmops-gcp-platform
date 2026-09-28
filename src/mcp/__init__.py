"""
Pacote do Servidor MCP (Model Context Protocol).
Expõe os microsserviços de contexto, ferramentas e recursos para agentes de IA no GCP.
"""

from src.mcp.mcp_server import mcp_app

__all__ = ["mcp_app"]
"""
Módulo da API FastAPI.
Expõe os roteadores e a aplicação principal para facilitar importações externas e testes.
"""

from src.api.main import app
from src.api.routes import router

__all__ = ["app", "router"]
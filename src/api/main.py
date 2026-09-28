from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import router as api_router
from src.config import settings
from src.mcp.mcp_server import mcp_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gere o ciclo de vida da aplicação (startup e shutdown).
    Inicializa conexões e recursos compartilhados no arranque e garante a libertação
    limpa de recursos ao encerrar a API.
    """
    # Ações de Startup: Logging de arranque e verificação de ambiente
    print(f"[STARTUP] A iniciar plataforma MLOps no ambiente: {settings.ENV}")
    yield
    # Ações de Shutdown: Encerrar pools de conexões se necessário
    print("[SHUTDOWN] A encerrar serviços da plataforma MLOps.")


app = FastAPI(
    title="GCP GenAI MLOps & LLMOps Platform API",
    description=(
        "Plataforma empresarial em produção para microsserviços de agentes GenAI, "
        "versionamento de prompts, contexto RAG, pipelines de avaliação e telemetria BigQuery no GCP."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configuração de CORS para permitir acessos controlados
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusão dos roteadores da API principal
app.include_router(api_router)

# Montagem do servidor MCP (Model Context Protocol) na sub-rota /mcp-server
app.mount("/mcp-server", mcp_app)


# Handler global para exceções não tratadas (evita expor stack traces sensíveis em produção)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Captura qualquer erro não tratado na aplicação e devolve uma resposta JSON padronizada,
    garantindo que o serviço permaneça resiliente sem derrubar o container.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=jsonable_encoder({
            "success": False,
            "error_type": exc.__class__.__name__,
            "message": "Ocorreu um erro interno na plataforma de MLOps.",
            "detail": str(exc) if settings.ENV == "development" else "Consulte os logs do Cloud Logging para mais detalhes."
        }),
    )


@app.get(
    "/",
    summary="Health Check e Estado do Sistema",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any]
)
async def root() -> Dict[str, Any]:
    """
    Endpoint de verificação de saúde (Health Check) utilizado pelo Cloud Run e Load Balancers
    para validar a disponibilidade do serviço.
    """
    return {
        "status": "online",
        "service": "GCP GenAI MLOps & LLMOps Platform",
        "environment": settings.ENV,
        "gcp_project": settings.GCP_PROJECT_ID,
        "gcp_region": settings.GCP_REGION,
        "docs": "/docs",
        "mcp_server_endpoint": "/mcp-server/mcp"
    }
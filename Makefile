# Makefile - Plataforma Enterprise GenAI & LLMOps no Google Cloud (GCP)
#
# Automatiza o ciclo de vida do desenvolvimento, execução local, compilação
# de pipelines do Vertex AI/Kubeflow e construção de imagens Docker.

.PHONY: help install test run-api run-mcp run-dashboard docker-build compile-pipelines deploy-gcp

# Configuração dos executáveis padrão do ambiente Python
PYTHON := python3
PIP    := pip

help:
	@echo "Enterprise GCP LLMOps Platform - Makefile Commands"
	@echo "----------------------------------------------------"
	@echo "make install           : Instala todas as dependências do projeto"
	@echo "make test              : Executa a suíte de testes unitários com pytest"
	@echo "make run-api           : Inicia o microserviço FastAPI (Agente de IA) localmente"
	@echo "make run-mcp           : Inicia o Servidor MCP (Model Context Protocol) localmente"
	@echo "make run-dashboard     : Inicia o Dashboard de Observabilidade Streamlit"
	@echo "make compile-pipelines : Compila os pipelines Kubeflow/Vertex AI para JSON"
	@echo "make docker-build      : Constrói as imagens Docker dos microserviços localmente"

install:
	$(PIP) install -r requirements.txt

test:
	pytest -v tests/

run-api:
	# Executa a API principal de agentes na porta 8080 com suporte a hot-reload
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8080

run-mcp:
	# Inicia o servidor do protocolo MCP na porta 8081 para chamadas de ferramentas
	uvicorn src.mcp.mcp_server:mcp_app --reload --host 0.0.0.0 --port 8081

run-dashboard:
	# Inicia a interface gráfica do Streamlit para monitoramento e métricas de LLM
	streamlit run dashboard/app.py --server.port 8501

compile-pipelines:
	# Compila as definições do Kubeflow Pipelines para artefatos JSON no Vertex AI
	$(PYTHON) pipelines/compile_pipelines.py

docker-build:
	# Constrói as imagens dos containers a partir dos Dockerfiles dedicados
	docker build -t llmops-agent-service:latest -f docker/Dockerfile.agent .
	docker build -t llmops-mcp-server:latest -f docker/Dockerfile.mcp .
from enum import Enum
from typing import Annotated

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentOption(str, Enum):
    """
    Garante validação estrita para o ambiente de execução evitando falhas de digitação.
    """
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Configurações centralizadas da plataforma de MLOps & LLMOps no GCP.
    Aplica validação de tipos, regras de valores e propriedades computadas.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Configurações de Ambiente e GCP
    ENV: EnvironmentOption = Field(
        default=EnvironmentOption.DEVELOPMENT,
        description="Ambiente de implantação da aplicação",
    )
    GCP_PROJECT_ID: Annotated[str, Field(min_length=1, description="ID do Projeto no Google Cloud")] = (
        "genai-mlops-platform"
    )
    GCP_REGION: str = Field(default="us-central1", description="Região padrão do GCP")

    # Configurações do Vertex AI
    VERTEX_MODEL_NAME: str = Field(
        default="gemini-1.5-pro", description="Modelo LLM principal no Vertex AI"
    )
    VERTEX_EMBEDDING_MODEL: str = Field(
        default="text-embedding-004", description="Modelo de embeddings para RAG"
    )
    VERTEX_EXPERIMENT_NAME: str = Field(
        default="llmops-prompt-eval", description="Nome do experimento no Vertex AI"
    )

    # Tabelas do BigQuery
    BQ_DATASET: str = Field(default="llmops_prod", description="Dataset do BigQuery")
    BQ_INFERENCE_TABLE: str = Field(
        default="inference_logs", description="Tabela de telemetria de inferências"
    )
    BQ_PROMPTS_TABLE: str = Field(
        default="prompt_versions", description="Tabela de versionamento de prompts"
    )
    BQ_EVAL_TABLE: str = Field(
        default="eval_metrics", description="Tabela de métricas de avaliação de RAG"
    )
    BQ_KNOWLEDGE_TABLE: str = Field(
        default="corporate_knowledge", description="Tabela de dados corporativos e embeddings"
    )

    # Custos por 1k Tokens (USD)
    # ge=0.0 impede que custos negativos sejam configurados por engano
    INPUT_TOKEN_COST_PER_1K: float = Field(
        default=0.00125, ge=0.0, description="Custo por 1k tokens de entrada"
    )
    OUTPUT_TOKEN_COST_PER_1K: float = Field(
        default=0.00375, ge=0.0, description="Custo por 1k tokens de saída"
    )

    # Flags de Execução e Telemetria
    MOCK_GCP_SERVICES: bool = Field(
        default=True, description="Flag para usar mocks locais durante testes"
    )
    ENABLE_BIGQUERY_LOGGING: bool = Field(
        default=True, description="Flag para habilitar logging assíncrono no BigQuery"
    )

    # Propriedades Computadas
    # Usamos @computed_field para centralizar a montagem dos URIs completos no BigQuery
    # evitando concatenação manual repetitiva ao longo do código.
    @computed_field
    @property
    def bq_inference_table_uri(self) -> str:
        """Retorna o URI completo da tabela de inferência: projeto.dataset.tabela"""
        return f"{self.GCP_PROJECT_ID}.{self.BQ_DATASET}.{self.BQ_INFERENCE_TABLE}"

    @computed_field
    @property
    def bq_eval_table_uri(self) -> str:
        """Retorna o URI completo da tabela de avaliação: projeto.dataset.tabela"""
        return f"{self.GCP_PROJECT_ID}.{self.BQ_DATASET}.{self.BQ_EVAL_TABLE}"

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calcula o custo total da requisição em USD com base na quantidade de tokens.
        Garante padronização no cálculo de custos em todos os serviços.
        """
        input_cost = (prompt_tokens / 1000.0) * self.INPUT_TOKEN_COST_PER_1K
        output_cost = (completion_tokens / 1000.0) * self.OUTPUT_TOKEN_COST_PER_1K
        return round(input_cost + output_cost, 6)


settings = Settings()
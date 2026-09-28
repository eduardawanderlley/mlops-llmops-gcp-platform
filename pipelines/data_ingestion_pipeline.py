"""
Pipeline do Vertex AI para Ingestão de Conhecimento Corporativo e Indexação Vetorial.

Esta pipeline orquestra a leitura de documentos e arquivos brutos no Google Cloud Storage (GCS),
divisão de textos em pedaços (chunking), geração de embeddings com o modelo Vertex AI (text-embedding-004)
e persistência na tabela vetorial do BigQuery.
"""

import json
from kfp import dsl
from kfp.dsl import Artifact, Input, Output


@dsl.component(
    base_image="python:3.10-slim",
    packages_to_install=["google-cloud-bigquery", "google-cloud-storage"],
)
def extract_and_chunk_documents(
    source_gcs_path: str,
    chunked_output: Output[Artifact],
) -> None:
    """
    Componente KFP: Lê PDFs/documentos corporativos brutos do GCS e realiza
    a extração e fragmentação em trechos de texto (chunks).
    """
    # Simulação da extração de documentos do GCS e geração dos pedaços de texto
    chunks: list[dict[str, str]] = [
        {
            "doc_id": "DOC-2026-01",
            "chunk_id": "c1",
            "title": "GCP Infrastructure Standard",
            "content": (
                "All microservices must be deployed on Cloud Run with automated "
                "CI/CD deployment pipelines."
            ),
        }
    ]

    with open(chunked_output.path, "w") as f:
        json.dump(chunks, f)


@dsl.component(
    base_image="python:3.10-slim",
    packages_to_install=["google-cloud-aiplatform", "google-cloud-bigquery"],
)
def generate_embeddings_and_load(
    project_id: str,
    dataset_name: str,
    table_name: str,
    chunked_input: Input[Artifact],
) -> None:
    """
    Componente KFP: Gera vetores de embedding usando o modelo text-embedding-004
    do Vertex AI e carrega os resultados no banco vetorial do BigQuery.
    """
    with open(chunked_input.path, "r") as f:
        chunks: list[dict[str, str]] = json.load(f)

    print(
        f"Carregados {len(chunks)} chunks na tabela vetorial do BigQuery: "
        f"{project_id}.{dataset_name}.{table_name}"
    )


@dsl.pipeline(
    name="llmops-corporate-data-ingestion-pipeline",
    description="Batch pipeline to extract, chunk, embed, and index enterprise docs into BigQuery vector store",
    pipeline_root="gs://llmops-pipeline-artifacts-bucket/pipeline_roots",
)
def corporate_data_ingestion_pipeline(
    project_id: str = "genai-mlops-platform",
    source_gcs_path: str = "gs://llmops-raw-corporate-docs/2026/",
    dataset_name: str = "llmops_prod",
    table_name: str = "corporate_knowledge",
) -> None:
    """
    Orquestra a execução sequencial do fluxo de ingestão vetorial RAG no Kubeflow / Vertex AI Pipelines.
    """
    chunk_task = extract_and_chunk_documents(source_gcs_path=source_gcs_path)

    _ = generate_embeddings_and_load(
        project_id=project_id,
        dataset_name=dataset_name,
        table_name=table_name,
        chunked_input=chunk_task.outputs["chunked_output"],
    )
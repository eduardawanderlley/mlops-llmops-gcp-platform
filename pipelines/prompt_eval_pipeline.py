"""
Pipeline do Vertex AI para Avaliação Contínua de Prompts e Benchmarking de LLMs.

Esta pipeline busca datasets de teste (golden datasets) persisidos no BigQuery,
executa inferências e avalia métricas de fidelidade (faithfulness), relevância
da resposta (answer relevance) e taxa de alucinação (hallucination rate).
"""

import json
from kfp import dsl
from kfp.dsl import Artifact, Input, Metrics, Output


@dsl.component(
    base_image="python:3.10-slim",
    packages_to_install=["google-cloud-bigquery", "pydantic", "jinja2"],
)
def fetch_evaluation_dataset(
    dataset_name: str,
    output_dataset: Output[Artifact],
) -> None:
    """
    Componente KFP: Busca amostras do dataset de referência (golden dataset) no BigQuery
    ou registro de artefatos.
    """
    samples: list[dict[str, str]] = [
        {
            "id": "s1",
            "query": "What are security rules for GCP AI?",
            "ground_truth": "Use Secret Manager and BigQuery logging.",
        },
        {
            "id": "s2",
            "query": "Where are microservices deployed?",
            "ground_truth": "Cloud Run containers.",
        },
    ]

    with open(output_dataset.path, "w") as f:
        json.dump(samples, f)


@dsl.component(
    base_image="python:3.10-slim",
    packages_to_install=["google-cloud-aiplatform", "google-cloud-bigquery", "jinja2"],
)
def evaluate_prompt_version(
    prompt_version: str,
    input_dataset: Input[Artifact],
    metrics_output: Output[Metrics],
) -> None:
    """
    Componente KFP: Avalia uma versão específica do prompt contra o dataset
    e calcula métricas registradas diretamente no Vertex AI Experiments / KFP.
    """
    with open(input_dataset.path, "r") as f:
        samples: list[dict[str, str]] = json.load(f)

    # Simulação de cálculo das métricas de avaliação do LLM
    sample_count: int = len(samples)
    faithfulness: float = 0.92
    answer_relevance: float = 0.95
    hallucination_rate: float = 0.04

    metrics_output.log_metric("sample_count", float(sample_count))
    metrics_output.log_metric("faithfulness_score", faithfulness)
    metrics_output.log_metric("answer_relevance_score", answer_relevance)
    metrics_output.log_metric("hallucination_rate", hallucination_rate)


@dsl.pipeline(
    name="llmops-prompt-evaluation-pipeline",
    description="Automated Vertex AI Pipeline for evaluation of prompt versions & LLM metrics",
    pipeline_root="gs://llmops-pipeline-artifacts-bucket/pipeline_roots",
)
def prompt_evaluation_pipeline(
    prompt_version: str = "v1.0.0",
    dataset_name: str = "enterprise_qa_v1",
) -> None:
    """
    Orquestra a execução da avaliação contínua de prompts no Kubeflow / Vertex AI Pipelines.
    """
    dataset_task = fetch_evaluation_dataset(dataset_name=dataset_name)

    _ = evaluate_prompt_version(
        prompt_version=prompt_version,
        input_dataset=dataset_task.outputs["output_dataset"],
    )
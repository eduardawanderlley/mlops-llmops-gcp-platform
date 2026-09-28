import os
from kfp.compiler import Compiler

from pipelines.data_ingestion_pipeline import corporate_data_ingestion_pipeline
from pipelines.prompt_eval_pipeline import prompt_evaluation_pipeline


def compile_all() -> None:
    """
    Compila todas as pipelines de Kubeflow/Vertex AI definidas no projeto
    para os respetivos arquivos JSON de especificação de execução.
    """
    output_dir: str = os.path.dirname(__file__)

    # Compilação da Pipeline de Avaliação de Prompts
    eval_pipeline_json: str = os.path.join(output_dir, "prompt_eval_pipeline.json")
    Compiler().compile(
        pipeline_func=prompt_evaluation_pipeline,
        package_path=eval_pipeline_json,
    )
    print(f"Pipeline de avaliação compilada com sucesso: {eval_pipeline_json}")

    # Compilação da Pipeline de Ingestão de Dados (RAG)
    ingest_pipeline_json: str = os.path.join(output_dir, "data_ingestion_pipeline.json")
    Compiler().compile(
        pipeline_func=corporate_data_ingestion_pipeline,
        package_path=ingest_pipeline_json,
    )
    print(f"Pipeline de ingestão compilada com sucesso: {ingest_pipeline_json}")


if __name__ == "__main__":
    compile_all()
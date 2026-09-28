-- Infrastructure as Code / BigQuery DDL para Plataforma LLMOps & GenAI
-- Dataset Target: llmops_prod (ou llmops_dev de acordo com o ambiente GCP)

-- Schema Principal da Plataforma
CREATE SCHEMA IF NOT EXISTS `llmops_prod`
OPTIONS (
  location = "us-central1",
  description = "Armazenamento de Telemetria LLMOps, Catálogo de Prompts, Métricas de Avaliação e Banco Vetorial"
);

-- Tabela 1: Logs de Telemetria e Inferência de LLMs
-- Particionada por data e clusterizada por versão do prompt e modelo
CREATE TABLE IF NOT EXISTS `llmops_prod.inference_logs` (
  request_id STRING OPTIONS(description = "UUID único de identificação de cada chamada ao agente"),
  timestamp TIMESTAMP OPTIONS(description = "Data e hora de início do processamento da requisição"),
  prompt_version STRING OPTIONS(description = "Versão semântica do prompt utilizado (ex: v1.2.0)"),
  model_name STRING OPTIONS(description = "Identificador do modelo no Vertex AI (ex: gemini-1.5-pro, text-embedding-004)"),
  user_id STRING OPTIONS(description = "Identificador do usuário corporativo ou sistema cliente"),
  input_prompt STRING OPTIONS(description = "Texto completo do prompt de entrada enviado ao modelo"),
  output_text STRING OPTIONS(description = "Resposta de texto gerada pelo modelo de IA"),
  input_tokens INT64 OPTIONS(description = "Quantidade de tokens de entrada processados"),
  output_tokens INT64 OPTIONS(description = "Quantidade de tokens de saída gerados"),
  total_tokens INT64 OPTIONS(description = "Total acumulado de tokens consumidos"),
  cost_usd NUMERIC OPTIONS(description = "Custo calculado em USD baseado na tabela do Vertex AI"),
  latency_ms FLOAT64 OPTIONS(description = "Latência total fim-a-fim da inferência em milissegundos"),
  status_code INT64 OPTIONS(description = "Código HTTP ou de status de execução (200 = Sucesso)"),
  error_message STRING OPTIONS(description = "Rastreio detalhado de erros em caso de falha de execução"),
  metadata JSON OPTIONS(description = "Objeto JSON flexível com contexto, cabeçalhos e histórico de chamadas de ferramentas")
)
PARTITION BY DATE(timestamp)
CLUSTER BY prompt_version, model_name
OPTIONS (
  description = "Tabela de logs de telemetria de alto volume para monitoramento de consumo de tokens, latência e custos."
);

-- Tabela 2: Registro e Governança de Versões de Prompts
-- Catálogo imutável para gestão do ciclo de vida de prompts
CREATE TABLE IF NOT EXISTS `llmops_prod.prompt_versions` (
  prompt_id STRING OPTIONS(description = "Identificador único do template do prompt (ex: rag-qa-agent)"),
  version STRING OPTIONS(description = "Versão semântica (ex: v1.2.0)"),
  template_text STRING OPTIONS(description = "String do template parametrizado em formato Jinja2"),
  system_instruction STRING OPTIONS(description = "Instruções de sistema (System Prompt) repassadas ao modelo"),
  default_model STRING OPTIONS(description = "Modelo recomendado no Vertex AI para esta versão de prompt"),
  parameters JSON OPTIONS(description = "Configuração de hiperparâmetros (temperature, top_p, top_k, max_tokens)"),
  created_by STRING OPTIONS(description = "E-mail do autor/engenheiro ou processo do pipeline de CI"),
  created_at TIMESTAMP OPTIONS(description = "Data e hora de criação do registro"),
  status STRING OPTIONS(description = "Status no ciclo de vida: DRAFT, STAGING, PRODUCTION, ARCHIVED"),
  change_log STRING OPTIONS(description = "Resumo das alterações realizadas e justificativa de avaliação"),
  PRIMARY KEY(prompt_id, version) NOT ENFORCED
)
OPTIONS (
  description = "Catálogo de prompts com governança e versionamento imutável entre ambientes."
);

-- Tabela 3: Métricas de Avaliação Contínua de LLMs (RAG/Prompt Eval)
-- Gerado por execuções do Vertex AI Pipelines / Kubeflow
CREATE TABLE IF NOT EXISTS `llmops_prod.eval_metrics` (
  eval_run_id STRING OPTIONS(description = "Identificador único da execução da pipeline de avaliação"),
  prompt_id STRING OPTIONS(description = "Identificador do prompt avaliado"),
  prompt_version STRING OPTIONS(description = "Versão do prompt submetida ao teste"),
  dataset_name STRING OPTIONS(description = "Nome do dataset de referência (golden dataset) utilizado"),
  sample_count INT64 OPTIONS(description = "Número total de amostras/testes avaliados"),
  faithfulness_score FLOAT64 OPTIONS(description = "Métrica de fidelidade/fundamentação dos fatos no RAG (0.0 a 1.0)"),
  answer_relevance_score FLOAT64 OPTIONS(description = "Score de relevância da resposta em relação ao prompt (0.0 a 1.0)"),
  context_precision_score FLOAT64 OPTIONS(description = "Precisão do contexto recuperado para o RAG"),
  hallucination_rate FLOAT64 OPTIONS(description = "Percentual detectado de alucinações"),
  avg_latency_ms FLOAT64 OPTIONS(description = "Latência média das chamadas durante a rodada de testes"),
  avg_cost_usd NUMERIC OPTIONS(description = "Custo médio por requisição de avaliação"),
  evaluated_at TIMESTAMP OPTIONS(description = "Data e hora de conclusão da avaliação"),
  evaluator_model STRING OPTIONS(description = "Modelo de LLM utilizado como juiz (ex: gemini-1.5-pro)")
)
PARTITION BY DATE(evaluated_at)
CLUSTER BY prompt_id, prompt_version
OPTIONS (
  description = "Métricas de avaliação contínua registradas por pipelines automatizadas de MLOps."
);

-- Tabela 4: Banco Conhecimento Corporativo / Busca Vetorial (RAG)
CREATE TABLE IF NOT EXISTS `llmops_prod.corporate_knowledge` (
  doc_id STRING OPTIONS(description = "Identificador do documento corporativo de origem"),
  chunk_id STRING OPTIONS(description = "Identificador único do trecho/fragmento dentro do documento"),
  title STRING OPTIONS(description = "Título do documento ou referência da fonte de dados"),
  content STRING OPTIONS(description = "Conteúdo de texto do fragmento utilizado no contexto do RAG"),
  category STRING OPTIONS(description = "Categoria do departamento ou domínio (ex: HR, Finance, IT)"),
  embedding ARRAY<FLOAT64> OPTIONS(description = "Vetor de embedding gerado via Vertex AI Embeddings API"),
  updated_at TIMESTAMP OPTIONS(description = "Data e hora da última sincronização do documento")
)
CLUSTER BY category
OPTIONS (
  description = "Base de conhecimento corporativa estruturada e integrada com o BigQuery Vector Search / Vertex AI."
);
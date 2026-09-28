-- Views Analíticas para Telemetria, Monitoramento de Custo e Performance LLMOps
-- Dataset Target: llmops_prod

-- View 1: Resumo Diário de Custos e Consumo de Tokens por Modelo e Prompt
CREATE OR REPLACE VIEW `llmops_prod.vw_daily_cost_summary` AS
SELECT
  DATE(timestamp) AS log_date,
  model_name,
  prompt_version,
  COUNT(1) AS total_requests,
  SUM(CASE WHEN status_code = 200 THEN 1 ELSE 0 END) AS successful_requests,
  SUM(CASE WHEN status_code != 200 THEN 1 ELSE 0 END) AS failed_requests,
  SUM(input_tokens) AS total_input_tokens,
  SUM(output_tokens) AS total_output_tokens,
  SUM(total_tokens) AS grand_total_tokens,
  ROUND(SUM(cost_usd), 4) AS total_cost_usd,
  ROUND(AVG(cost_usd), 6) AS avg_cost_per_request
FROM
  `llmops_prod.inference_logs`
GROUP BY
  log_date,
  model_name,
  prompt_version;

-- View 2: Percentis de Latência (p50, p90, p95, p99) por Versão de Prompt
-- Utiliza aproximação de percentis agregados para performance analítica
CREATE OR REPLACE VIEW `llmops_prod.vw_latency_performance` AS
SELECT
  prompt_version,
  model_name,
  COUNT(1) AS sample_size,
  ROUND(AVG(latency_ms), 2) AS avg_latency_ms,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(50)] AS p50_latency_ms,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(90)] AS p90_latency_ms,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(95)] AS p95_latency_ms,
  APPROX_QUANTILES(latency_ms, 100)[OFFSET(99)] AS p99_latency_ms
FROM
  `llmops_prod.inference_logs`
WHERE
  status_code = 200
GROUP BY
  prompt_version,
  model_name;

-- View 3: Leaderboard de Prompts (Métricas de Avaliação x Telemetria Real)
CREATE OR REPLACE VIEW `llmops_prod.vw_prompt_leaderboard` AS
WITH eval_summary AS (
  SELECT
    prompt_id,
    prompt_version,
    AVG(faithfulness_score) AS avg_faithfulness,
    AVG(answer_relevance_score) AS avg_relevance,
    AVG(hallucination_rate) AS avg_hallucination_rate,
    MAX(evaluated_at) AS latest_eval_time
  FROM
    `llmops_prod.eval_metrics`
  GROUP BY
    prompt_id,
    prompt_version
),
prod_telemetry AS (
  SELECT
    prompt_version,
    COUNT(1) AS prod_volume,
    AVG(latency_ms) AS prod_avg_latency_ms,
    SUM(cost_usd) AS prod_total_cost_usd
  FROM
    `llmops_prod.inference_logs`
  GROUP BY
    prompt_version
)
SELECT
  pv.prompt_id,
  pv.version,
  pv.status,
  pv.default_model,
  COALESCE(es.avg_faithfulness, 0.0) AS faithfulness_score,
  COALESCE(es.avg_relevance, 0.0) AS answer_relevance_score,
  COALESCE(es.avg_hallucination_rate, 0.0) AS hallucination_rate,
  COALESCE(pt.prod_volume, 0) AS production_requests_count,
  ROUND(COALESCE(pt.prod_avg_latency_ms, 0.0), 2) AS prod_avg_latency_ms,
  ROUND(COALESCE(pt.prod_total_cost_usd, 0.0), 4) AS prod_total_cost_usd,
  pv.created_at
FROM
  `llmops_prod.prompt_versions` pv
LEFT JOIN eval_summary es
  ON pv.prompt_id = es.prompt_id AND pv.version = es.prompt_version
LEFT JOIN prod_telemetry pt
  ON pv.version = pt.prompt_version;
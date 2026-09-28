import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "GCP GenAI MLOps" in data["service"]


def test_chat_completions_endpoint():
    payload = {
        "prompt_id": "rag-qa-agent",
        "prompt_version": "v1.0.0",
        "user_query": "What are the GCP security policies for AI?",
        "user_id": "test_user_001",
        "use_rag": True,
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "request_id" in data
    assert "output_text" in data
    assert data["prompt_version"] == "v1.0.0"
    assert data["input_tokens"] > 0
    assert data["cost_usd"] >= 0.0


def test_list_prompts():
    response = client.get("/v1/prompts")
    assert response.status_code == 200
    catalog = response.json()
    assert "v1.0.0" in catalog


def test_register_prompt():
    payload = {
        "version": "v2.0.0-test",
        "template": "Hello {{ query }}",
        "model": "gemini-1.5-pro",
    }
    response = client.post("/v1/prompts", json=payload)
    assert response.status_code == 200
    assert response.json()["version"] == "v2.0.0-test"


def test_run_eval_endpoint():
    payload = {"prompt_version": "v1.0.0", "dataset_name": "enterprise_qa_v1"}
    response = client.post("/v1/eval/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "faithfulness_score" in data
    assert "answer_relevance_score" in data
    assert "hallucination_rate" in data
    assert data["prompt_version"] == "v1.0.0"


def test_telemetry_metrics_endpoint():
    response = client.get("/v1/telemetry/metrics")
    assert response.status_code == 200
    metrics = response.json()
    assert "total_requests" in metrics
    assert "total_cost_usd" in metrics
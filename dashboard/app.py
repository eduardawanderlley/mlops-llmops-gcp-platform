import os
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

# Configuração da página do Streamlit
st.set_page_config(
    page_title="GCP LLMOps & GenAI Platform Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Resolução dinâmica da URL base da API a partir de variáveis de ambiente
API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8080/v1")


@st.cache_resource
def get_http_session() -> requests.Session:
    """
    Cria e armazena em cache uma instância do requests.Session.
    O reuso da sessão HTTP evita o overhead de handshake TCP/TLS a cada requisição efetuada pela UI.
    """
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def make_api_request(
    method: str,
    endpoint: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: int = 15,
) -> Optional[Dict[str, Any]]:
    """
    Cliente de requisição HTTP resiliente para a API FastAPI do backend.
    Isola o tratamento de exceções de rede e timeouts para impedir crash da interface do Streamlit.
    """
    session: requests.Session = get_http_session()
    url: str = f"{API_BASE_URL}{endpoint}"

    try:
        if method.upper() == "POST":
            response = session.post(url, json=payload, timeout=timeout)
        else:
            response = session.get(url, timeout=timeout)

        if response.status_code == 200:
            return response.json()

        st.error(f"Erro na API ({response.status_code}): {response.text}")
        return None
    except requests.exceptions.Timeout:
        st.error("Tempo de requisição esgotado (Timeout). Verifique a disponibilidade do backend.")
        return None
    except requests.exceptions.ConnectionError:
        st.error(f"Falha ao conectar no microsserviço backend em {API_BASE_URL}")
        return None
    except Exception as ex:
        st.error(f"Erro inesperado ao se comunicar com a API: {ex}")
        return None


# Cabeçalho da Aplicação
st.title("⚡ Enterprise GCP MLOps & LLMOps Platform")
st.markdown("### Production GenAI Observability, Prompt Version Governance, and BigQuery Telemetry")

# Barra lateral com diagnóstico de saúde da API
with st.sidebar:
    st.header("⚙️ Configurações")
    st.info(f"**Endpoint da API Backend:**\n`{API_BASE_URL}`")
    if st.button("🔄 Health Check"):
        health_data: Optional[Dict[str, Any]] = make_api_request("GET", "/health", timeout=5)
        if health_data:
            st.success(f"Status: {health_data.get('status', 'online')}")

# Divisão por abas para isolar os casos de uso
tab_chat, tab_obs, tab_eval, tab_catalog = st.tabs([
    "🚀 Agent Chat & RAG",
    "📊 LLMOps Observability & Costs",
    "🧪 Continuous Evaluation & Leaderboard",
    "📜 Prompt Catalog",
])

# Aba 1: Execução do Agente GenAI com RAG
with tab_chat:
    st.subheader("Live GenAI Agent Inference (Vertex AI + BigQuery RAG)")

    col_config, col_chat = st.columns([1, 2])

    with col_config:
        prompt_version: str = st.selectbox(
            "Prompt Template Version",
            ["v1.0.0", "v1.1.0-optimized"],
        )
        category: str = st.selectbox(
            "Corporate Knowledge Filter",
            ["All", "Security", "Architecture", "Finance"],
        )
        use_rag: bool = st.checkbox("Enable RAG Context Ingestion", value=True)
        user_id: str = st.text_input("User / Service Principal ID", value="engineer@company.com")

    with col_chat:
        query: str = st.text_area(
            "User Query",
            value="What are the security guidelines and container hosting requirements for GCP AI microservices?",
            height=120,
        )

        if st.button("Run Inference Request", type="primary"):
            payload: Dict[str, Any] = {
                "prompt_id": "rag-qa-agent",
                "prompt_version": prompt_version,
                "user_query": query,
                "user_id": user_id,
                "category_filter": None if category == "All" else category,
                "use_rag": use_rag,
            }

            with st.spinner("Processing request via Vertex AI & logging to BigQuery..."):
                data: Optional[Dict[str, Any]] = make_api_request("POST", "/chat/completions", payload=payload, timeout=20)

                if data:
                    st.success("Response Received & Telemetry Recorded!")
                    st.markdown(f"**Agent Output:**\n\n{data.get('output_text', '')}")

                    st.divider()
                    m1, m2, m3, m4 = st.columns(4)
                    req_id: str = str(data.get("request_id", "N/A"))
                    m1.metric("Request ID", req_id[:8] + "..." if len(req_id) > 8 else req_id)
                    m2.metric("Latency", f"{data.get('latency_ms', 0)} ms")
                    m3.metric("Total Tokens", data.get("total_tokens", 0))
                    m4.metric("Cost (USD)", f"${data.get('cost_usd', 0.0):.6f}")

                    if data.get("rag_context_used"):
                        with st.expander("Retrieved Corporate Knowledge Chunks"):
                            st.json(data["rag_context_used"])

# Aba 2: Métricas de Observabilidade e Custos em Tempo Real
with tab_obs:
    st.subheader("Real-Time Telemetry & BigQuery Cost Analytics")

    if st.button("Refresh Telemetry"):
        with st.spinner("Fetching consolidated metrics..."):
            metrics: Optional[Dict[str, Any]] = make_api_request("GET", "/telemetry/metrics")

            if metrics:
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Total Requests Processed", metrics.get("total_requests", 0))
                k2.metric("Total Cost Accumulated", f"${metrics.get('total_cost_usd', 0.0):.4f}")
                k3.metric("Average End-to-End Latency", f"{metrics.get('avg_latency_ms', 0.0):.2f} ms")
                k4.metric("Total Tokens Consumed", metrics.get("total_tokens", 0))

                latest_records: List[Dict[str, Any]] = metrics.get("latest_records", [])
                if latest_records:
                    st.subheader("Latest Telemetry Logs (BigQuery Stream)")
                    df: pd.DataFrame = pd.DataFrame(latest_records)
                    
                    # Filtra colunas disponíveis para evitar exceções de KeyError
                    desired_cols: List[str] = [
                        "request_id",
                        "timestamp",
                        "prompt_version",
                        "model_name",
                        "input_tokens",
                        "output_tokens",
                        "cost_usd",
                        "latency_ms",
                    ]
                    cols_to_show: List[str] = [c for c in desired_cols if c in df.columns]
                    st.dataframe(df[cols_to_show], use_container_width=True)

# Aba 3: Avaliação Contínua e Benchmark de Prompts
with tab_eval:
    st.subheader("Vertex AI Pipeline Continuous Evaluation")

    eval_version: str = st.selectbox(
        "Select Prompt Version for Benchmark Evaluation",
        ["v1.0.0", "v1.1.0-optimized"],
    )

    if st.button("Run Evaluation Pipeline"):
        with st.spinner("Running automated evaluation suite against golden dataset..."):
            eval_data: Optional[Dict[str, Any]] = make_api_request(
                "POST",
                "/eval/run",
                payload={"prompt_version": eval_version},
                timeout=30,
            )

            if eval_data:
                st.success("Evaluation Pipeline Run Completed!")

                e1, e2, e3, e4 = st.columns(4)
                e1.metric("Faithfulness / Grounding", f"{eval_data.get('faithfulness_score', 0.0) * 100:.1f}%")
                e2.metric("Answer Relevance", f"{eval_data.get('answer_relevance_score', 0.0) * 100:.1f}%")
                e3.metric("Hallucination Rate", f"{eval_data.get('hallucination_rate', 0.0) * 100:.1f}%")
                e4.metric("Average Latency", f"{eval_data.get('avg_latency_ms', 0.0):.2f} ms")

                details: List[Dict[str, Any]] = eval_data.get("sample_details", [])
                if details:
                    st.subheader("Sample-level Breakdown")
                    st.dataframe(pd.DataFrame(details), use_container_width=True)

# Aba 4: Catálogo e Governança de Templates de Prompt
with tab_catalog:
    st.subheader("Prompt Version Governance Catalog")

    catalog: Optional[Dict[str, Any]] = make_api_request("GET", "/prompts")
    if catalog:
        for version_id, details in catalog.items():
            model_name: str = details.get("model", "N/A") if isinstance(details, dict) else "N/A"
            template_code: str = details.get("template", "") if isinstance(details, dict) else ""
            
            with st.expander(f"Version {version_id} - Model: {model_name}"):
                st.code(template_code, language="jinja2")
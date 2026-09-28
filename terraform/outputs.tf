output "agent_service_url" {
  description = "Public URL for Agent Microservice on Cloud Run"
  value       = google_cloud_run_v2_service.agent_service.uri
}

output "mcp_server_url" {
  description = "Public URL for MCP Server on Cloud Run"
  value       = google_cloud_run_v2_service.mcp_server.uri
}

output "artifact_registry_repository" {
  description = "Artifact Registry Docker Repository ID"
  value       = google_artifact_registry_repository.docker_repo.id
}

output "bigquery_dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.llmops_dataset.dataset_id
}

output "service_account_email" {
  description = "Platform Service Account Email"
  value       = google_service_account.llmops_sa.email
}
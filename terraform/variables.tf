variable "project_id" {
  type        = string
  description = "GCP Project ID"
  default     = "genai-mlops-platform"
}

variable "region" {
  type        = string
  description = "GCP Region for Cloud Run & Vertex AI"
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
  default     = "prod"
}

variable "agent_service_name" {
  type        = string
  description = "Cloud Run service name for Agent Microservice"
  default     = "llmops-agent-service"
}

variable "mcp_service_name" {
  type        = string
  description = "Cloud Run service name for MCP Server"
  default     = "llmops-mcp-server"
}
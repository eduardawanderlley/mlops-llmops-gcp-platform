terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.15.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "gcp_apis" {
  for_each = toset([
    "run.googleapis.com",
    "aiplatform.googleapis.com",
    "bigquery.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com"
  ])
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_service_account" "llmops_sa" {
  account_id   = "llmops-platform-sa"
  display_name = "LLMOps Platform Runtime Service Account"
}

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.llmops_sa.email}"
}

resource "google_project_iam_member" "bigquery_admin" {
  project = var.project_id
  role    = "roles/bigquery.admin"
  member  = "serviceAccount:${google_service_account.llmops_sa.email}"
}

resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.region
  repository_id = "llmops-container-repo"
  description   = "Artifact Registry Repository for MLOps & LLMOps Container Images"
  format        = "DOCKER"

  depends_on = [google_project_service.gcp_apis]
}

resource "google_storage_bucket" "pipeline_artifacts" {
  name                        = "${var.project_id}-pipeline-artifacts-${var.environment}"
  location                    = var.region
  force_destroy               = true
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

resource "google_bigquery_dataset" "llmops_dataset" {
  dataset_id                  = "llmops_${var.environment}"
  friendly_name               = "LLMOps Production Telemetry & Vector Store"
  description                 = "BigQuery Dataset for LLMOps Telemetry, Prompt Catalog, Evaluation Metrics, and Vector Store"
  location                    = var.region
  default_table_expiration_ms = null

  labels = {
    env = var.environment
  }
}

resource "google_cloud_run_v2_service" "agent_service" {
  name     = var.agent_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.llmops_sa.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.name}/agent-service:latest"

      env {
        name  = "ENV"
        value = var.environment
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "BQ_DATASET"
        value = google_bigquery_dataset.llmops_dataset.dataset_id
      }

      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
      }
    }
  }

  depends_on = [google_project_service.gcp_apis]
}

resource "google_cloud_run_v2_service" "mcp_server" {
  name     = var.mcp_service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.llmops_sa.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.docker_repo.name}/mcp-server:latest"

      env {
        name  = "ENV"
        value = var.environment
      }
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "1Gi"
        }
      }
    }
  }

  depends_on = [google_project_service.gcp_apis]
}

resource "google_cloud_run_v2_service_iam_member" "agent_service_public" {
  location = google_cloud_run_v2_service.agent_service.location
  name     = google_cloud_run_v2_service.agent_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "mcp_server_public" {
  location = google_cloud_run_v2_service.mcp_server.location
  name     = google_cloud_run_v2_service.mcp_server.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
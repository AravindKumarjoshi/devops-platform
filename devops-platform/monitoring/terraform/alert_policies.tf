terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  type        = string
  description = "The GCP project ID"
  default     = "enterprise-monitoring"
}

variable "region" {
  type        = string
  description = "The GCP region"
  default     = "us-central1"
}

variable "pagerduty_service_key" {
  type        = string
  description = "PagerDuty integration key"
  sensitive   = true
}

variable "alert_email" {
  type        = string
  description = "Email address for alerts"
  default     = "platform-sre@enterprise.com"
}

# Notification Channels
resource "google_monitoring_notification_channel" "email" {
  display_name = "SRE Email Alerts"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

resource "google_monitoring_notification_channel" "pagerduty" {
  display_name = "SRE PagerDuty"
  type         = "pagerduty"
  labels = {
    service_key = var.pagerduty_service_key
  }
}

# Alert Policies
resource "google_monitoring_alert_policy" "gke_pod_crashloopbackoff" {
  display_name = "GKE Pod CrashLoopBackOff"
  combiner     = "OR"
  conditions {
    display_name = "Container Restart Count > 3 in 5m"
    condition_threshold {
      filter          = "resource.type=\"k8s_container\" AND metric.type=\"kubernetes.io/container/restart_count\" AND metric.labels.reason=\"CrashLoopBackOff\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 3
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }
  notification_channels = [
    google_monitoring_notification_channel.email.name,
    google_monitoring_notification_channel.pagerduty.name
  ]
}

resource "google_monitoring_alert_policy" "vm_cpu_saturation" {
  display_name = "VM CPU Saturation > 85%"
  combiner     = "OR"
  conditions {
    display_name = "CPU utilization > 85% for 10m"
    condition_threshold {
      filter          = "resource.type=\"gce_instance\" AND metric.type=\"compute.googleapis.com/instance/cpu/utilization\""
      duration        = "600s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.85
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  notification_channels = [
    google_monitoring_notification_channel.email.name,
    google_monitoring_notification_channel.pagerduty.name
  ]
}

resource "google_monitoring_alert_policy" "vm_memory_saturation" {
  display_name = "VM Memory Saturation > 90%"
  combiner     = "OR"
  conditions {
    display_name = "Memory utilization > 90% for 5m"
    condition_threshold {
      filter          = "resource.type=\"gce_instance\" AND metric.type=\"agent.googleapis.com/memory/percent_used\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 90
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  notification_channels = [
    google_monitoring_notification_channel.email.name,
    google_monitoring_notification_channel.pagerduty.name
  ]
}

resource "google_monitoring_alert_policy" "gke_node_not_ready" {
  display_name = "GKE Node Not Ready"
  combiner     = "OR"
  conditions {
    display_name = "Node Ready Status is False"
    condition_threshold {
      filter          = "resource.type=\"k8s_node\" AND metric.type=\"kubernetes.io/node/condition\" AND metric.labels.condition=\"Ready\""
      duration        = "300s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  notification_channels = [
    google_monitoring_notification_channel.email.name,
    google_monitoring_notification_channel.pagerduty.name
  ]
}

resource "google_monitoring_alert_policy" "jenkins_build_queue_deep" {
  display_name = "Jenkins Build Queue Deep"
  combiner     = "OR"
  conditions {
    display_name = "Jenkins Queue > 10"
    condition_threshold {
      filter          = "resource.type=\"k8s_container\" AND metric.type=\"custom.googleapis.com/jenkins_queue_size_value\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  notification_channels = [
    google_monitoring_notification_channel.email.name,
    google_monitoring_notification_channel.pagerduty.name
  ]
}

output "alert_policy_ids" {
  value = {
    crashloopbackoff = google_monitoring_alert_policy.gke_pod_crashloopbackoff.id
    cpu_saturation   = google_monitoring_alert_policy.vm_cpu_saturation.id
    mem_saturation   = google_monitoring_alert_policy.vm_memory_saturation.id
    node_not_ready   = google_monitoring_alert_policy.gke_node_not_ready.id
    jenkins_queue    = google_monitoring_alert_policy.jenkins_build_queue_deep.id
  }
  description = "IDs of the created alert policies"
}

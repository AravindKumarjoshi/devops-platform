packer {
  required_version = ">= 1.11.0"
  required_plugins {
    googlecompute = {
      source  = "github.com/hashicorp/googlecompute"
      version = "~> 1.1"
    }
    ansible = {
      source  = "github.com/hashicorp/ansible"
      version = "~> 1.1"
    }
  }
}

variable "project_id" {
  type    = string
  default = "enterprise-images"
}

variable "zone" {
  type    = string
  default = "us-central1-a"
}

variable "source_image_family" {
  type    = string
  default = "rhel-9"
}

variable "image_family" {
  type    = string
  default = "enterprise-rhel9-base"
}

variable "network" {
  type    = string
  default = "projects/enterprise-vpc-host/global/networks/shared-vpc"
}

variable "subnetwork" {
  type    = string
  default = "projects/enterprise-vpc-host/regions/us-central1/subnetworks/gke-nodes-subnet"
}

variable "machine_type" {
  type    = string
  default = "n2-standard-4"
}

variable "disk_size_gb" {
  type    = number
  default = 50
}

variable "image_storage_location" {
  type    = string
  default = "us"
}

variable "ansible_playbook_path" {
  type    = string
  default = "./ansible-playbook.yaml"
}

variable "build_number" {
  type    = string
  default = "0"
}

variable "git_commit_sha" {
  type    = string
  default = "unknown"
}

source "googlecompute" "base_image" {
  project_id                  = var.project_id
  zone                        = var.zone
  source_image_family         = var.source_image_family
  machine_type                = var.machine_type
  disk_size                   = var.disk_size_gb
  disk_type                   = "pd-ssd"
  network                     = var.network
  subnetwork                  = var.subnetwork
  use_internal_ip             = true
  omit_external_ip            = true
  tags                        = ["packer-build", "allow-ssh-iap"]
  service_account_email       = "packer-builder@enterprise-images.iam.gserviceaccount.com"
  scopes                      = ["https://www.googleapis.com/auth/cloud-platform"]
  image_name                  = "${var.image_family}-${var.build_number}-${substr(var.git_commit_sha, 0, 8)}"
  image_family                = var.image_family
  image_labels = {
    built_by     = "packer"
    build_number = var.build_number
    git_sha      = var.git_commit_sha
    base_os      = var.source_image_family
    environment  = "production"
    managed_by   = "gitops"
  }
  image_storage_locations     = [var.image_storage_location]
  metadata = {
    enable-oslogin        = "TRUE"
    block-project-ssh-keys = "TRUE"
  }
  wait_to_add_ssh_keys        = "30s"
  communicator                = "ssh"
  use_iap                     = true
}

build {
  sources = ["source.googlecompute.base_image"]

  provisioner "shell" {
    inline = [
      "echo 'Updating packages and installing Ansible prerequisites...'",
      "if command -v dnf >/dev/null 2>&1; then sudo dnf update -y && sudo dnf install -y python3 python3-pip ansible-core; elif command -v apt-get >/dev/null 2>&1; then sudo apt-get update -y && sudo apt-get install -y python3 python3-pip python3-apt ansible; fi",
      "echo 'Prerequisites installed.'"
    ]
  }

  provisioner "ansible" {
    playbook_file = var.ansible_playbook_path
    extra_arguments = ["-v", "--diff"]
    ansible_env_vars = ["ANSIBLE_HOST_KEY_CHECKING=False"]
  }

  provisioner "shell" {
    inline = [
      "echo 'Cleaning up image...'",
      "sudo rm -f ~/.bash_history /root/.bash_history",
      "sudo rm -f /etc/ssh/ssh_host_*",
      "sudo rm -rf /tmp/*",
      "sudo truncate -s 0 /var/log/messages || true",
      "sudo truncate -s 0 /var/log/syslog || true",
      "sudo truncate -s 0 /var/log/auth.log || true",
      "sudo truncate -s 0 /var/log/secure || true",
      "if command -v apt-get >/dev/null 2>&1; then sudo apt-get clean && sudo rm -rf /var/lib/apt/lists/*; elif command -v dnf >/dev/null 2>&1; then sudo dnf clean all; fi",
      "echo 'Cleanup complete.'"
    ]
  }
}

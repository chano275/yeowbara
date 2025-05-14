terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.17"
    }
  }
}

provider "google" {
  credentials = file("~/.ssh/pure-wall-454723-t7-f0d4b183c12d.json") # 네 서비스 계정 키 파일
  project     = var.project_id
  region      = var.region
}


# ───── VPC 방화벽 (클러스터 포트) ─────
resource "google_compute_firewall" "k8s_ports" {
  name    = "k8s-cluster-ports-new"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["6443", "10250"]
  }
  allow {
    protocol = "udp"
    ports    = ["8472", "4789"]
  }
  target_tags = ["k8s-node"]
  source_ranges = ["172.26.0.0/16"]
}

# ───── 워커 노드 ─────
resource "google_compute_instance" "k8s_worker" {
  name         = "k8s-worker-1"
  zone         = var.zone
  machine_type = "e2-medium"
  tags         = ["k8s-node"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 50
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }

  metadata_startup_script = <<-EOT
    #!/bin/bash
    set -euxo pipefail

    # 1) 시스템 기본 설정
    swapoff -a
    sed -i '/ swap / s/^/#/' /etc/fstab
    apt-get update -y
    apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

    # 2) containerd 설치
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
      > /etc/apt/sources.list.d/docker.list
    apt-get update -y && apt-get install -y containerd.io
    mkdir -p /etc/containerd
    containerd config default > /etc/containerd/config.toml
    sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
    systemctl enable --now containerd

    # 3) 커널 파라미터
    modprobe overlay
    modprobe br_netfilter
    cat <<SYSCTL >/etc/sysctl.d/k8s.conf
    net.bridge.bridge-nf-call-iptables  = 1
    net.bridge.bridge-nf-call-ip6tables = 1
    net.ipv4.ip_forward                 = 1
    SYSCTL
    sysctl --system

    # 4) Kubernetes 1.29 설치
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.29/deb/Release.key \
      | gpg --dearmor -o /etc/apt/keyrings/kubernetes-archive-keyring.gpg
    echo "deb [signed-by=/etc/apt/keyrings/kubernetes-archive-keyring.gpg] \
      https://pkgs.k8s.io/core:/stable:/v1.29/deb/ /" \
      > /etc/apt/sources.list.d/kubernetes.list
    apt-get update -y
    apt-get install -y kubelet=1.29.*-1.1 kubeadm=1.29.*-1.1 kubectl=1.29.*-1.1
    apt-mark hold kubelet kubeadm kubectl
    systemctl enable --now kubelet

    # 5) 워커 노드 조인
    ${var.join_command}
  EOT

  metadata = {
    ssh-keys = "ubuntu:${file(var.ssh_pub)}"
  }
}


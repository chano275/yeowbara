terraform {
  required_version = ">= 1.6"
  required_providers {
    ncloud = {
      source  = "NaverCloudPlatform/ncloud"
      version = "~> 2.0"
    }
  }
}

provider "ncloud" {
  access_key   = var.access_key
  secret_key   = var.secret_key
  region       = var.region
  site         = var.site
  support_vpc  = true
}

##############################
# 1. 이미지 · 스펙 데이터 소스
##############################

# Ubuntu 22.04 이미지
data "ncloud_image_product" "ubuntu" {
  filter {
    name   = "product_code"
    values = ["SW.VSVR.OS.LNX64.UBNTU.SVR2204"]
  }
}

# 서버 스펙 (4 vCPU, 8GB)
data "ncloud_server_product" "standard" {
  server_image_product_code = data.ncloud_image_product.ubuntu.product_code
  filter {
    name   = "product_type"
    values = ["STAND"]
  }
  filter {
    name   = "cpu_count"
    values = ["4"]
  }
  filter {
    name   = "memory_size"
    values = ["8GB"]
  }
}

##############################
# 2. 네트워크 (VPC/서브넷/ACG)
##############################

resource "ncloud_vpc" "vpc" {
  name            = "k8s-vpc"
  ipv4_cidr_block = "10.0.0.0/16"
}

resource "ncloud_subnet" "subnet" {
  name           = "k8s-subnet"
  vpc_no         = ncloud_vpc.vpc.id
  subnet         = cidrsubnet(ncloud_vpc.vpc.ipv4_cidr_block, 8, 1)
  zone           = var.zone
  network_acl_no = ncloud_vpc.vpc.default_network_acl_no
  subnet_type    = "PUBLIC"
}

resource "ncloud_access_control_group" "acg" {
  name        = "k8s-acg"
  vpc_no      = ncloud_vpc.vpc.id
  description = "K8s cluster security group"
}

# SSH, API server, kubelet, flannel, HTTP/HTTPS 허용
resource "ncloud_access_control_group_rule" "acg_rules" {
  for_each = {
    ssh     = { protocol = "TCP", ip = "0.0.0.0/0", ports = "22",    desc = "SSH" }
    api     = { protocol = "TCP", ip = "0.0.0.0/0", ports = "6443",  desc = "K8s API" }
    kubelet = { protocol = "TCP", ip = "0.0.0.0/0", ports = "10250", desc = "Kubelet" }
    flannel = { protocol = "UDP", ip = "0.0.0.0/0", ports = "8472",  desc = "Flannel VXLAN" }
    http    = { protocol = "TCP", ip = "0.0.0.0/0", ports = "80",    desc = "HTTP" }
    https   = { protocol = "TCP", ip = "0.0.0.0/0", ports = "443",   desc = "HTTPS" }
  }

  access_control_group_no = ncloud_access_control_group.acg.id

  inbound {
    protocol    = each.value.protocol
    ip_block    = each.value.ip
    port_range  = each.value.ports
    description = each.value.desc
  }
}

##############################
# 3. Init 스크립트 (worker join)
##############################

resource "ncloud_init_script" "init" {
  name    = "k8s-worker-init"
  content = <<-EOT
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
}

##############################
# 4. 서버 · NIC · Public IP
##############################

resource "ncloud_server" "k8s_worker" {
  name                      = "k8s-worker-1"
  server_product_code       = data.ncloud_server_product.standard.server_product_code
  server_image_product_code = data.ncloud_image_product.ubuntu.product_code
  subnet_no                 = ncloud_subnet.subnet.id
  login_key_name            = var.login_key_name
  init_script_no            = ncloud_init_script.init.id
}

resource "ncloud_network_interface" "nic" {
  name                  = "k8s-worker-nic"
  subnet_no             = ncloud_subnet.subnet.id
  access_control_groups = [ncloud_access_control_group.acg.id]
  server_instance_no    = ncloud_server.k8s_worker.id
}

resource "ncloud_public_ip" "public_ip" {
  server_instance_no = ncloud_server.k8s_worker.id
}

##############################
# 5. Outputs
##############################

output "server_instance_id" {
  value = ncloud_server.k8s_worker.id
}

output "server_public_ip" {
  value = ncloud_public_ip.public_ip.public_ip
}

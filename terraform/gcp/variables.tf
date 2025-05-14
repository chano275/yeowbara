variable "project_id" {
  description = "GCP 프로젝트 ID"
  type        = string
  default     = "pure-wall-454723-t7"
}

variable "region" {
  description = "GCP 리전"
  type        = string
  default     = "asia-northeast3"
}

variable "zone" {
  description = "GCP 존"
  type        = string
  default     = "asia-northeast3-a"
}

variable "ssh_pub" {
  description = "로컬 SSH 공개키 경로"
  type        = string
  default     = "~/.ssh/my-gcp-key.pub"
}

variable "join_command" {
  description = "kubeadm join 명령어"
  type        = string
  default     = "kubeadm join k12b107.p.ssafy.io:6443 --token 2649av.fegkl8o3h46gccoq --discovery-token-ca-cert-hash sha256:42577587792472850a6f1511c81480b06d14803b3d78322c853d44edd0b9ef4c"
}

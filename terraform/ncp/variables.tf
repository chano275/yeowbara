variable "access_key" {
  description = "NCP API 접근 키"
  type        = string
  default     = "ncp_iam_BPAMKR2neBwb9el4LHCl"
}

variable "secret_key" {
  description = "NCP API 시크릿 키"
  type        = string
  default     = "ncp_iam_BPKMKR5gBV2OvXGYgD82wF8AcpAxztInUI"
}

variable "region" {
  description = "NCP 리전"
  type        = string
  default     = "KR"
}

variable "site" {
  description = "NCP 사이트"
  type        = string
  default     = "public"
}

variable "zone" {
  description = "NCP 존"
  type        = string
  default     = "KR-2"
}

variable "join_command" {
  description = "kubeadm join 명령어"
  type        = string
  default     = "kubeadm join k12b107.p.ssafy.io:6443 --token 2649av.fegkl8o3h46gccoq --discovery-token-ca-cert-hash sha256:42577587792472850a6f1511c81480b06d14803b3d78322c853d44edd0b9ef4c"
}

variable "login_key_name" {
  description = "NCP 로그인 키 이름"
  type        = string
  default     = "tf-key" # NCP 콘솔에서 생성한 로그인 키 이름
}

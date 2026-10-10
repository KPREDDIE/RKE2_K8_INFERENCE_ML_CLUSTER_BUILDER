variable "kubeconfig_path" {
  type        = string
  description = "Path to the RKE2 kubeconfig (never commit it)."
}

variable "gpu_nodes" {
  type        = list(string)
  description = "Node names that have NVIDIA GPUs."
  default     = []
}

variable "gpu_node_pool_label" {
  type        = string
  description = "Value for the inference/pool label on GPU nodes."
  default     = "gpu-inference"
}

variable "gpu_operator_version" {
  type    = string
  default = "v24.9.2"
}

variable "keda_version" {
  type    = string
  default = "2.16.0"
}

variable "prometheus_address" {
  type        = string
  description = "In-cluster Prometheus URL KEDA queries for queue depth."
  default     = "http://kube-prometheus-stack-prometheus.monitoring.svc:9090"
}

resource "kubernetes_namespace" "gpu_operator" {
  metadata { name = "gpu-operator" }
}

resource "kubernetes_namespace" "inference" {
  metadata { name = "inference" }
}

# Label GPU nodes so the chart can target them.
resource "kubernetes_labels" "gpu_nodes" {
  for_each    = toset(var.gpu_nodes)
  api_version = "v1"
  kind        = "Node"
  metadata { name = each.value }
  labels = {
    "inference/pool" = var.gpu_node_pool_label
  }
}

# NVIDIA GPU Operator on RKE2: the containerd paths differ from upstream.
resource "helm_release" "gpu_operator" {
  name       = "gpu-operator"
  namespace  = kubernetes_namespace.gpu_operator.metadata[0].name
  repository = "https://helm.ngc.nvidia.com/nvidia"
  chart      = "gpu-operator"
  version    = var.gpu_operator_version

  # Drivers preinstalled on the host? set driver.enabled=false.
  set {
    name  = "driver.enabled"
    value = "true"
  }
  set {
    name  = "toolkit.env[0].name"
    value = "CONTAINERD_CONFIG"
  }
  set {
    name  = "toolkit.env[0].value"
    value = "/var/lib/rancher/rke2/agent/etc/containerd/config.toml.tmpl"
  }
  set {
    name  = "toolkit.env[1].name"
    value = "CONTAINERD_SOCKET"
  }
  set {
    name  = "toolkit.env[1].value"
    value = "/run/k3s/containerd/containerd.sock"
  }
  set {
    name  = "toolkit.env[2].name"
    value = "CONTAINERD_RUNTIME_CLASS"
  }
  set {
    name  = "toolkit.env[2].value"
    value = "nvidia"
  }
  set {
    name  = "toolkit.env[3].name"
    value = "CONTAINERD_SET_AS_DEFAULT"
  }
  set {
    name  = "toolkit.env[3].value"
    value = "true"
    type  = "string"
  }
}

# KEDA scales the engines on queue depth read from Prometheus.
resource "helm_release" "keda" {
  name             = "keda"
  namespace        = "keda"
  create_namespace = true
  repository       = "https://kedacore.github.io/charts"
  chart            = "keda"
  version          = var.keda_version
}

# Deploy the engine chart. Duplicate this block (or use for_each) per model.
resource "helm_release" "llm_server" {
  name      = "llama-vllm"
  namespace = kubernetes_namespace.inference.metadata[0].name
  chart     = "${path.module}/../helm/llm-server"

  values = [file("${path.module}/../helm/llm-server/values.yaml")]

  set {
    name  = "autoscaling.prometheusAddress"
    value = var.prometheus_address
  }

  depends_on = [helm_release.gpu_operator, helm_release.keda, kubernetes_labels.gpu_nodes]
}

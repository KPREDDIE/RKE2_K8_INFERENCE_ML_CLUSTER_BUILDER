# RKE2 GPU inference cluster builder

- `terraform/` – GPU Operator (RKE2 containerd paths), KEDA, GPU node labels, and a `helm_release` of the engine chart.
- `helm/llm-server/` – one chart, `engine: vllm | sglang`. Deployment, PVC model cache, Service, ServiceMonitor, KEDA ScaledObject.

## Use
```bash
cd terraform
terraform init
terraform apply -var-file=example.tfvars
# switch engine
helm upgrade llama-vllm ../helm/llm-server -n inference --set engine=sglang
```

## Notes
- Create the HF token secret first: `kubectl -n inference create secret generic hf-token --from-literal=HF_TOKEN=...`
- Queue-depth metrics: `vllm:num_requests_waiting` (vLLM), `sglang:num_queue_reqs` (SGLang, needs `--enable-metrics`).
  Verify the exact names and labels against your engine version's `/metrics` and adjust the PromQL in `scaledobject.yaml`.
- Scale-down cooldown is long on purpose: model load takes minutes.
- Pin image tags to versions you have tested. Not yet validated against a live cluster (no helm/terraform in the authoring environment).

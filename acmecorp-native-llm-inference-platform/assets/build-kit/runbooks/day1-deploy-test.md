# Day 1 — GPU, model, serving and validation

**Owner:** Platform/LLMOps engineer. **Entry:** Day 0 exit and authorized workload context.
**Exit:** live acceptance evidence attached to release; failed checks remain visible.

## GPU and GitOps bootstrap

Confirm nodes Ready and their actual labels/resources. GPU Operator requires cluster-scoped
CRDs, RBAC and privileged host access in its own protected namespace. Restricted Pod Security
for inference does not apply unchanged to this operator namespace; document the scoped exception.
Mirror/pin its chart and every rendered image. Use platform/gpu-operator.values.yaml as values
for the validated v26.7.1 chart, not as an apply-able Kubernetes object. Render with Helm and
server-dry-run before adoption. The RKE2 containerd socket is /run/k3s/containerd/containerd.sock.
Use CDI; validate across a worker reboot. Toolkit changes can restart RKE2, so expect lab outage.

Bootstrap Argo CD with a reviewed immutable install artifact under the normal bootstrap identity.
It then owns the GPU/add-on/inference resources. Fleet and RKE2 HelmChart must not own the same
objects. For a one-time manual demo apply, explicitly record temporary bootstrap ownership and
adopt the exact manifests into Argo before ongoing changes. Do not use helm upgrade in parallel.
Record desired Git commit, Argo Synced/Healthy and observed image IDs; those are separate facts.

## Stage the model

Obtain the pinned Qwen snapshot in a controlled download/mirror environment. Validate provenance,
license, safetensors, tokenizer/config and any custom code. Materialize a clean read-only directory
with every file in config/model-files.json. Derive hashes from verified upstream/mirrored artifacts,
then independently compare the served copy. Never bless unknown local files by hashing them and
calling that provenance. Keep the master snapshot in durable private storage.

```powershell
$ModelDirectory = Read-Host 'Materialized model snapshot directory'
python scripts/verify_model.py --root $ModelDirectory --inventory config/model-files.json
```

Create/bind an existing acmecorp-model PVC in acmecorp-inference using the approved storage
provisioner. A local PV requires kubernetes.io/hostname affinity to the same site.json GPU node,
Retain reclaim policy and correct UID/GID 10001 read permissions. Keep model storage distinct
from Elemental's install disk and partition lifecycle. This kit does not fabricate a CSI provider.
Ensure the namespace exists through the same bootstrap owner before creating its PVC.

## Render and review serving

Set runtime_image to the verified digest; inspect the image's exact SGLang/CUDA version and
non-root startup. Configure the GPU hostname and support-evidence reference.

```powershell
$WorkloadContext = Read-Host 'Approved workload context'
python scripts/render.py workload --output generated/workload-001.json
kubectl --context $WorkloadContext apply --dry-run=server -f generated/workload-001.json
kubectl --context $WorkloadContext diff -f generated/workload-001.json
```

After the approved GitOps synchronization (or recorded bootstrap apply), use:

```powershell
kubectl --context $WorkloadContext get nodes
kubectl --context $WorkloadContext -n acmecorp-inference get pvc,pods,services,networkpolicies
kubectl --context $WorkloadContext -n acmecorp-inference rollout status deployment/sglang --timeout=1800s
```

The verifier hashes the full model before loading. Thirty minutes is a startup allowance, not
an SLO; measure actual storage and startup time. The demo Recreate strategy needs no spare GPU
but has downtime. Do not add a PDB promising availability that one replica cannot provide.

## Smoke and additional acceptance

Use the README localhost port-forward and smoke commands. RBAC needs nodes get/list and
namespace pods/deployments get/list; the separate tunnel needs pods/portforward create and
service/pod reads. No secret reads or cluster writes are needed by the smoke script.

| Suite | Procedure and pass condition | Evidence |
|---|---|---|
| Static | Offline tests; pinned references; rendered schema; secret and image scans | Tool versions/results and manifest hashes |
| Host/GPU | Supported tuple; nvidia-smi, driver and memory inventory; CDI CUDA test after reboot | Sanitized hardware report and runtime image IDs |
| Inference | Supplied smoke all PASS; separate model quality/safety synthetic cases | smoke JSON; approved evaluation scores |
| Network | Unlabeled client denied; approved scrape to 30001 permitted and inference to 30000 denied from that scraper; no public service; model pod egress denied | Authorized negative-test report |
| Telemetry | SGLang/DCGM series visible; no content-bearing labels; no raw body logging | Scrape/label audit with synthetic leak canary |
| Performance | Cold/warm startup and requests; p50/p95 TTFT, ITL, throughput, queueing and HBM | Workload/version/concurrency and distributions |
| Recovery | Prior model/runtime/config rollback; worker rebuild; management restore isolated | Timed restore/rollback record |

Negative tests, CUDA jobs, drain/restart and load generation mutate or consume resources and
must be executed under the lab test change, not hidden inside smoke. Define SLO targets before
measurement; no synthetic example numbers count as results. OTel traces/enterprise gateway,
OIDC denial, per-tenant quotas and cache isolation are extension tests, not passes for this demo.

## Telemetry configuration extensions

Choose direct Prometheus scraping or the metrics-only OTel collector config. Both require
approved digest-pinned deployment/chart manifests in observability with the matching
acmecorp.metrics-client=true pod label. Adjust namespace/service names if site.json changed.
The values/config files are not standalone deployments. Capture real metric names before making
dashboard queries or alert thresholds. GPU Operator supplies DCGM; verify its ServiceMonitor or
scrape integration explicitly. Keep Grafana private and secrets external. No Honeycomb egress
or fabricated dashboard metrics are enabled here.

### Review-fix deployment notes

Prometheus and OTel targets now use 30001. Apply the full workload bundle to include the
metrics proxy ConfigMap script, sidecar and Service port. Review any other policy allowing
port 30000. Smoke requires approved model-files.json beside site.json (or --inventory PATH).
It verifies the expected model/release identity and checksum-init success. Prefer the service
tunnel because an arbitrary gateway's routing cannot be proven by its returned model alias.

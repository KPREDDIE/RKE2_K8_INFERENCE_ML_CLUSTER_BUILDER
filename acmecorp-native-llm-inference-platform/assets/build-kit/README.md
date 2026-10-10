# ACMECORP Native LLM Inference Platform — engineer build kit

A private, single-tenant bare-metal Supermicro/RKE2 demonstrator. **Elemental/OS Manager and
Rancher own OS and RKE2 lifecycle.** No Ansible. This kit renders artifacts; it never deploys
implicitly. Current pins are integration candidates, and unresolved inputs intentionally block rendering.

## What is supplied

- Elemental MachineRegistration, SeedImage, selector and Rancher Cluster renderer.
- SGLang Deployment, model checksum init container, ClusterIP and NetworkPolicy renderer.
- GPU Operator values; Prometheus/OTel configuration extensions.
- Strict model verification, bounded inference smoke and runtime inventory scripts.
- Offline regression tests, TOGAF traceability, inventory, Day 0/1/2 and handoff playbooks.

## Assumptions and prerequisites

Use a separate, supported Rancher management cluster with Elemental CRDs/operator and trusted
TLS. The workload demo uses one physical server and one GPU worker: 80 GiB+ GPU VRAM,
128 GiB+ worker RAM and enough private storage for the complete model snapshot. The proposal
uses Qwen3.6-27B BF16 with a 4096-token context, two active requests and one GPU. Sizing is an
assumption, not a benchmark. There is no HA, client gateway, production authorization or live evidence.

Local tooling: Python 3.12+ (stdlib scripts), PowerShell 7+ for examples, kubectl compatible with
the target API, Helm for reviewed chart rendering. Tests have no Python package dependencies.
Target hosts are Linux managed by Elemental; do not run manual host commands as a second lifecycle.
Use PowerShell consistently on the workstation. Host diagnostics below are executed in a separately
identified Linux console session. Paths resolve from scripts; examples assume the kit directory.

## Start offline

Read the [operator quick start](runbooks/operator-quickstart.md). Run `python scripts/prepare.py --check` to list unresolved inputs together; use `--output generated/review-001` to render both manifests once inputs are resolved.

```powershell
python -m unittest discover -s tests -v
python scripts/render.py elemental --output generated/elemental.json
python scripts/render.py workload --output generated/workload.json
```

The two renders should initially fail with unresolved input errors. Fill config/elemental.json
and config/site.json, and supply config/model-files.json from independently verified artifacts.
Do not replace nulls with invented values. Reusing an output filename is refused to preserve review history.

1. Read [Day 0](runbooks/day0-elemental.md), record hardware/disks and supported component matrix.
2. Resolve immutable seed/host and SGLang runtime image digests. Verify signatures/scans and license.
3. Materialize the exact model revision on an existing read-only PVC; verify every file.
4. Render, review and server-dry-run against explicitly chosen authorized contexts.
5. Follow [Day 1](runbooks/day1-deploy-test.md) for deployment handoff, port-forward and smoke.
6. Exercise [Day 2](runbooks/day2-operations.md) and complete [handoff](runbooks/operations-handoff.md).

## Important configuration contract

config/elemental.json: use the actual Rancher-compatible RKE2 patch; an Elemental seed image
by digest; a support-evidence reference; operator SSH **public** key; verified /dev/disk/by-id
install targets. Root password login must be disabled in the approved image. Protect registration
URLs, generated seed media and kubeconfigs outside the repository.

config/site.json: supply the mirrored SGLang image as repo@sha256:..., verified GPU hostname,
existing model PVC and compatibility-evidence reference. Set pod_security_version to the target
Kubernetes minor after any support-matrix change. Use the linux/amd64 image manifest digest,
not a multiarch index, so smoke can compare the observed runtime digest directly. The image must support Python 3,
SGLang 0.5.21, UID/GID 10001 and read-only root filesystem with writable /tmp. Test those
properties; a digest alone does not prove them. If the vendor image fails, derive a reviewed
non-root image, scan it, and pin its new digest. Do not turn off security settings silently.

config/model-files.json: retain model ID and immutable commit and add every actual model file
with its independently verified SHA-256. Include config, tokenizer, weights, templates and license.
Materialize symlinks; remove download-cache metadata from the served snapshot. No extra files
are permitted. The checksum init container runs before the server and fails on any mismatch.
A checksum proves identity relative to the approved inventory, not safety of model behavior.

## Smoke (after authorized deployment)

In one terminal, start a localhost-only tunnel using the approved workload context:

```powershell
$WorkloadContext = Read-Host 'Approved workload context'
kubectl --context $WorkloadContext -n acmecorp-inference port-forward --address 127.0.0.1 service/sglang 30000:30000
```

In another terminal:

```powershell
$WorkloadContext = Read-Host 'Same approved workload context'
python scripts/smoke.py --context $WorkloadContext --site config/site.json --endpoint http://127.0.0.1:30000 --output evidence/smoke-001.json
```

Smoke makes Kubernetes reads and two bounded synthetic inference requests (one streamed),
checks exact SMOKE_OK output, GPU capacity, pod image digests, model/release/inventory identity, checksum-init success, node/PVC placement, rollout and metrics. It returns
nonzero on failure and records no output content, tokens or raw errors. For a separately approved
HTTPS gateway, pass --auth-file with a temporary token file; redirects are refused. Metrics are
same-origin; use the tunnel if the gateway has a different metrics route. Streaming evidence
checks protocol completion, not TTFT/ITL performance. There are no automatic retries or load tests. Each HTTP call has a total 60-second deadline, including DNS/TLS; use --request-deadline 1..300 to change it. Supply --inventory if model-files.json is not beside --site. An arbitrary gateway cannot be attested by alias matching; use the tunnel to the selected context.

## Scope of evidence

Local tests verify tooling behavior only. Server dry-run checks API/CRD schemas but cannot prove
GPU startup. Actual acceptance still requires host compatibility, model quality/safety, negative
network/RBAC tests, metrics privacy, performance, management-plane restore, worker rebuild and
rollback evidence. [Requirements](architecture/requirements.csv) initially remain not-run.
TOGAF alignment does not mean architecture approval, PCI certification or FIPS validation.

## Layout

config/ = reviewed inputs; scripts/ = local helpers; platform/ = GPU chart values;
observability/ = configuration extensions; architecture/ = traceability and decisions;
runbooks/ = operator procedures; tests/ = offline tests; versions/ = candidate baseline.
generated/ and evidence/ are local ignored outputs. Retain reviewed release evidence in the
approved private artifact store. Never put secrets, registration media or model weights in Git.

## Monitoring access change

Scrape `sglang.<namespace>.svc.cluster.local:30001/metrics` through the restricted Python
sidecar. Inference port 30000 remains available through the authorized localhost tunnel.
Apply the complete workload bundle and update scraper targets. Review existing additive
NetworkPolicies that may still grant monitoring clients port 30000. The sidecar uses the
same pinned image without a GPU allocation. Custom namespaces must also be reflected in
telemetry configuration. Validate proxy startup and live network isolation at acceptance.

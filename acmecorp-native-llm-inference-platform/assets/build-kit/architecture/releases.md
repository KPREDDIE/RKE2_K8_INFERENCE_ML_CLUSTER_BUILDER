# Release baseline and source record

Checked **2026-10-09 (America/Phoenix)**. These are identified upstream release candidates for
integration, not a jointly certified support matrix. No preview/nightly tags are selected.
"Latest stable model" is scoped to the selected downloadable Qwen dense model family, not all
vendors, hosted services, multimodal families or research checkpoints.

| Component | Identified release | Official evidence |
|---|---|---|
| Qwen dense open-weight model | Qwen3.6-27B | [Model card](https://huggingface.co/Qwen/Qwen3.6-27B), [publisher announcement](https://qwen.ai/blog?id=qwen3.6-27b) |
| Model snapshot | 6a9e13bd6fc8f0983b9b99948120bc37f49c13e9 | [Publisher API metadata](https://huggingface.co/api/models/Qwen/Qwen3.6-27B) |
| SGLang | 0.5.21 | [Release](https://github.com/sgl-project/sglang/releases/tag/v0.5.21) |
| RKE2 | v1.37.1+rke2r1 | [Release](https://github.com/rancher/rke2/releases/tag/v1.37.1%2Brke2r1) |
| Rancher Community | v2.15.2 | [Release](https://github.com/rancher/rancher/releases/tag/v2.15.2) |
| Elemental operator | v1.9.2 | [Release](https://github.com/rancher/elemental-operator/releases/tag/v1.9.2) |
| NVIDIA GPU Operator | v26.7.1 | [Release](https://github.com/NVIDIA/gpu-operator/releases/tag/v26.7.1) |
| Argo CD | v3.5.4 | [Release](https://github.com/argoproj/argo-cd/releases/tag/v3.5.4) |
| OTel Collector Contrib (extension) | v0.162.0 | [Release](https://github.com/open-telemetry/opentelemetry-collector-releases/releases/tag/v0.162.0) |

The model is Apache-2.0 according to its card; record the mirrored LICENSE and model card hash
and confirm intended-use policy. The model card recommends SGLang >=0.5.10. Its full-context
examples do not establish that this demo's hardware meets any latency or quality target.
The SGLang 0.5.21 NVIDIA image is a CUDA 13 build; select the driver through NVIDIA compatibility
rules. Do not retain an old CUDA/driver assumption from the original skill.

## Support and unresolved artifacts

Rancher Community release numbering is not Rancher Prime support entitlement. The
[SUSE support matrix](https://www.suse.com/suse-rancher/support-matrix/all-supported-versions/)
resolved to Rancher v2.14.4 at review time. A newer Community release does not establish that
RKE2 1.37, Elemental 1.9.2, the chosen OS and GPU Operator are a supported Prime combination.
Before deployment, record the actual compatible combination. If the newest release is outside
that matrix, choose the latest supported patch of the compatible minor and record the deviation.
Do not deploy the candidate combination simply because all releases exist.

Resolve these site inputs before rendering: seed/host image digest, exact OS/kernel and packages,
Supermicro model/BIOS/BMC, GPU/NIC firmware, driver, GPU topology, OCI runtime image digest,
model file hashes, storage and trusted registry. Render currently accepts an evidence reference;
it does not independently attest that referenced compatibility evidence is correct.

NVIDIA [platform support](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/platform-support.html)
and [RKE2 GPU integration](https://docs.rke2.io/add-ons/gpu_operators) must be checked against the
selected OS. CDI is the baseline with containerd 2; do not copy old config.toml.tmpl overrides or
experimental NRI settings. Toolkit installation may restart RKE2 through containerd; schedule it.

The Elemental seed is not merely a Linux ISO. Use the compatible Elemental/OS Manager media
with verified CA trust and operator CRDs. [OS Manager documentation](https://documentation.suse.com/cloudnative/os-manager/)
and [Elemental CLI flow](https://elemental.docs.rancher.com/quickstart-cli/) define the resource
workflow. Do not copy example root passwords, debug flags, mutable tags or disabled TLS verification.

## Refresh procedure

Record release URL/date/prerelease status; compare vendor support matrices; pin versions and
resolve registry digests and exact model revision; mirror and verify provenance; produce host,
container, model and configuration SBOMs; scan and disposition findings; run the test matrix;
record rollback. Refresh one compatibility boundary at a time. Do not silently update pinned
artifacts while deploying. Upstream stable status and local acceptance are separate decisions.

RKE2 enables secrets encryption by default; verify its actual status during acceptance. The renderer
does not inject the K3s-only secrets-encryption boolean. See the [RKE2 server configuration](https://docs.rke2.io/reference/server_config).
Elemental GitHub release status is not proof of stable SUSE chart-channel availability: resolve the
operator and CRD chart packages from the stable vendor channel and record the mapping before use.

## Refresh on 9 October 2026

Rechecked the upstream stable release pages linked above. Argo CD advances from 3.5.3 to
3.5.4; its release notes include security fixes. Other component pins are unchanged.
Elemental 1.9.2 remains marked Latest even though older-branch backports appear first in
its release list. Preserve the reviewed Qwen snapshot rather than tracking a moving main branch.
No new host/GPU support qualification was performed. The prior Prime matrix observation
above is historical; resolve current entitlement and the compatible tuple at the site gate.
The build never resolves `latest` or downloads runtime dependencies during deployment.

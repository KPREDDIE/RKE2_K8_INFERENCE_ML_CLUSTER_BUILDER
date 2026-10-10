# ACMECORP Native LLM Inference Platform — demonstrator skill

## Introduction

### What this project does

This project provides a repeatable build kit for running a large language model (LLM) on
physical Supermicro servers with NVIDIA GPUs. It prepares a private inference service: an
application sends a prompt, and the locally hosted model generates a response. The proposed
lab configuration uses Qwen3.6-27B served by SGLang on a single GPU worker, with a separate
workload control-plane server and an existing independent Rancher management cluster.

The deliverable is an installable AI-assistant skill and a self-contained operator kit with
configuration templates, Kubernetes manifest generators, model-integrity checks, smoke tests,
architecture records and operating instructions. Operators supply verified site values; the
kit then produces files for review and controlled deployment. It does not provision physical
machines simply by being downloaded or built.

### Why it exists

A bare-metal inference service depends on more than a model and a GPU. Host images, firmware,
drivers, Kubernetes, model storage, access controls and recovery procedures must work together.
This project makes those dependencies explicit so platform engineers, security reviewers and
operations staff can evaluate the same design and reproduce the same build.

Its purpose is to reduce manual setup errors, configuration drift and uncertain ownership.
Version pins, model checksums, private networking, automated checks and documented handoff
steps make changes easier to inspect and troubleshoot. The current deliverable is a
single-tenant demonstrator with synthetic prompts; production readiness requires additional
hardware, security, availability and recovery evidence.

### BMAD / CodeSpec development strategy

The project follows a **specification-to-code-to-evidence** workflow. In BMAD/CodeSpec terms,
planning defines the intended outcome and architecture; implementation turns that agreed
contract into code; review and tests check whether the result meets it. This aligns with
[BMAD's planning and build approach](https://docs.bmad-method.org/) and the
[CodeSpec specification-driven workflow](https://github.com/LucivHuang/CodeSpec/blob/main/README.EN.md).
Here these names describe the method alignment: the repository contains requirements and
validation artifacts, but does not record execution of either framework's own tooling.

The strategy is visible in five steps:

1. **Define the outcome and constraints.** Requirements name the capability, accountable owner,
   implementation, test and evidence needed for acceptance.
2. **Record design decisions.** Architecture records establish the topology, lifecycle owners,
   model identity, private access boundary and known limitations before deployment.
3. **Implement the contract.** Python renderers convert reviewed site configuration into
   manifests; the buildspec requires validation before packaging. Missing critical inputs
   block preparation instead of being replaced with guessed values.
4. **Review and test the result.** Regression tests cover expected behavior and failure cases.
   Review findings become tracked fixes, such as release-identity checks and metrics isolation.
5. **Hand over with evidence.** Human reviewers inspect the artifacts and authorize site work.
   Live smoke, performance and recovery results establish acceptance; local tests alone do not.

Review the [requirements](acmecorp-native-llm-inference-platform/assets/build-kit/architecture/requirements.csv),
[design decisions](acmecorp-native-llm-inference-platform/assets/build-kit/architecture/decisions.md)
and [validation record](VALIDATION.md) to trace this process. TOGAF supplies the architecture
review structure; BMAD/CodeSpec alignment describes the development workflow.

### Technology stack

| Layer | Technology | Role in the project |
|---|---|---|
| Physical compute | Supermicro servers, NVIDIA GPU, local NVMe | Host execution and replaceable cache; sizing requires site validation |
| Host lifecycle | Elemental / OS Manager | Register hosts and manage approved OS images with compatible NVIDIA drivers |
| Cluster management | Rancher and bare-metal RKE2 | Provision and manage Kubernetes directly on physical hosts |
| GPU integration | NVIDIA GPU Operator and CDI | Make host GPUs available to workloads; this profile disables operator driver installation |
| Model serving | SGLang and pinned Qwen3.6-27B snapshot | Provide inference with bounded context and concurrency |
| Model storage | Approved private artifact store and existing read-only Kubernetes PVC | Preserve authoritative model files and mount the verified serving copy |
| Workload delivery | Git, Argo CD and Helm chart values | Define reviewed desired state; bootstrap and controller ownership remain explicit |
| Observability | Prometheus, metrics-only OpenTelemetry configuration, NVIDIA DCGM and private Grafana | Supply monitoring configuration extensions requiring site deployment and validation |
| Build and validation | Python 3.12+, PowerShell 7+, JSON manifests, kubectl and optional schema tooling | Generate, inspect, test and package the operator kit |
| Governance | TOGAF records, release evidence and Day 0/1/2 runbooks | Support architecture review, operational acceptance and controlled change |

The [release baseline](acmecorp-native-llm-inference-platform/assets/build-kit/versions/candidates.json)
records component pins. Upstream stable releases still require a compatible, supported hardware
and software combination at the deployment site.

### How human reviewers should use it

Start with the purpose and scope above, then inspect the requirements, architecture decisions
and **Issues** section below. Confirm that the proposed topology and ownership match the lab.
Use the [operator quick start](acmecorp-native-llm-inference-platform/assets/build-kit/runbooks/operator-quickstart.md)
to generate a fresh kit, identify missing inputs and prepare a review bundle. Reviewers do not
need to install the assistant skill to read the documents or run the standalone kit.

Run the offline build checks, inspect the generated manifests and confirm image/model identity,
physical disk mapping, private access and rollback arrangements. The deployment owner then
follows Day 0 for host provisioning, Day 1 for inference deployment and validation, and Day 2
for operations and recovery. Keep management and workload contexts distinct. Complete the
[operations handoff](acmecorp-native-llm-inference-platform/assets/build-kit/runbooks/operations-handoff.md)
only after the required site evidence exists. Commands and detailed procedures follow below.

## Deliverables

- [Skill entrypoint](acmecorp-native-llm-inference-platform/SKILL.md)
- [Build-kit README](acmecorp-native-llm-inference-platform/assets/build-kit/README.md)
- [Day 0: Elemental and physical host provisioning](acmecorp-native-llm-inference-platform/assets/build-kit/runbooks/day0-elemental.md)
- [Day 1: GPU, model, deployment and smoke](acmecorp-native-llm-inference-platform/assets/build-kit/runbooks/day1-deploy-test.md)
- [Day 2: operations and recovery](acmecorp-native-llm-inference-platform/assets/build-kit/runbooks/day2-operations.md)
- [Architecture and TOGAF alignment](acmecorp-native-llm-inference-platform/assets/build-kit/architecture/togaf.md)
- [Gap review](acmecorp-native-llm-inference-platform/references/gap-review.md)
- [Release evidence process](acmecorp-native-llm-inference-platform/assets/build-kit/runbooks/release-evidence.md)
- [Local validation and outstanding live checks](VALIDATION.md)

## Model and release refresh

As checked **9 October 2026**, the selected downloadable model is **Qwen3.6-27B**, pinned to
`6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`, with **SGLang 0.5.21**.
The upstream platform candidates are **RKE2 v1.37.1+rke2r1**, **Rancher Community v2.15.2**,
**Elemental operator v1.9.2**, **GPU Operator v26.7.1**, and **Argo CD v3.5.4**.
The proposed starting profile is one 80 GiB GPU, BF16, TP=1 and a 4096-token context.

These are verified release identities, not a verified hardware/support combination. In particular,
Rancher Community and Rancher Prime supported versions may differ, and a GitHub Elemental release
does not establish stable vendor-chart availability. Use the supported intersection at deployment.
The [dated release record and official sources](acmecorp-native-llm-inference-platform/assets/build-kit/architecture/releases.md)
explain those boundaries. No global "newest model" claim is made across unrelated model families.

## Generate a project

Use Python 3.12+ from this distribution directory:

```powershell
python acmecorp-native-llm-inference-platform/scripts/scaffold.py --output platform-build-kit
python -m unittest discover -s platform-build-kit/tests -v
```

The generated kit is self-contained. Rendering makes no cluster connection. Its unresolved
image/disk/model-hash inputs intentionally fail closed until real site values are supplied.
Read its README before using live management or workload contexts.

## Install the skill

Choose the skill destination recognized by your agent/project. Copy the **whole skill directory**,
including assets and references, or use the supplied copy helper:

```powershell
$SkillDestination = Read-Host 'Full new destination directory for this skill'
python acmecorp-native-llm-inference-platform/scripts/install.py --destination $SkillDestination
```

The installer refuses existing destinations. For upgrades, review the diff and preserve the old
installation before selecting a new destination. It does not alter global agent configuration.
The .skill file is a ZIP with one skill-directory root; clients that do not import .skill directly
can extract it. Select the skill with your agent's supported invocation mechanism.

Example task: "Use this skill to generate the Elemental-managed ACMECORP DEV demonstrator kit.
Use synthetic prompts, preserve private endpoints, and generate reviewable files only."

## Validate and rebuild the distribution

```powershell
python tools/validate.py
python tools/package.py
```

Outputs: release/acmecorp-native-llm-inference-platform.skill,
release/acmecorp-llm-demonstrator.zip and release/CHECKSUMS.txt. The ZIP contains the source and
packager so it can rebuild itself. Original input archives, generated local projects, model weights,
registration media, credentials, caches and local evidence are excluded. Each archive also contains
member checksums. Archive checksum verification proves integrity, not publisher authenticity.

Optional vendor-schema validation uses PyYAML/jsonschema and downloaded official schemas, as
described in VALIDATION.md. The normal kit tests use only Python's standard library.

## Acceptance boundary

Local artifact checks pass; **no bare-metal installation or live cluster smoke was performed**.
OS/kernel/firmware/driver compatibility, immutable runtime/media digests, model file hashes,
Rancher Cluster server validation, performance, privacy, restore and rollback need site evidence.
TOGAF deliverables are supplied for review; organizational compliance requires human decisions.
Production, public exposure, enterprise gateway, HA and PCI/FIPS approval are outside this demo.

## Issues from the 9 October review

| Priority | Finding | Resolution in this revision | Remaining verification |
|---|---|---|---|
| P1 | Smoke could pass the wrong model release with the same runtime and alias. | Compare pod and deployment release/model/inventory annotations; require successful checksum init, expected node and PVC. Save expected identity in evidence. | Live release validation and independent endpoint/tunnel ownership verification. |
| P2 | Monitoring access to port 30000 also allowed inference. | Metrics-only sidecar on 30001; monitoring policy permits only that port and proxy forwards only exact GET /metrics. | Live negative network tests, including inference attempts from the monitoring pod. |
| P2 | A trickling stream could exceed the nominal timeout. | HTTP worker has a total deadline; incremental SSE stops at DONE and caps response bytes. | Actual gateway/runtime validation. |

All three have local regression coverage. Compatibility, model quality, performance,
restore and rollback remain open; local tests are not a bare-metal deployment acceptance.

## Build and operator quick start

`buildspec.json` is the portable offline build contract, not an AWS CodeBuild configuration.
It references the candidate baseline; validation always precedes packaging. Use Python 3.12+.
If `python` opens Windows Store, use the full path to a working interpreter. Source paths
resolve from the scripts, so tools/build.py also works when invoked from another directory.

```powershell
python tools/build.py --check
python tools/build.py --output release/2026-10-09
```

Choose a new release directory each time. Existing archives are preserved. The source ZIP
includes the buildspec and tools to rebuild itself. No automatic install or live apply occurs.
For a fresh operator kit:

```powershell
python acmecorp-native-llm-inference-platform/scripts/scaffold.py --output platform-build-kit-v2
python platform-build-kit-v2/scripts/prepare.py --check
# Fill the listed inputs using approved evidence, then:
python platform-build-kit-v2/scripts/prepare.py --output platform-build-kit-v2/generated/review-001
```

Supplied null inputs intentionally produce exit code 2. Follow the
[operator guide](acmecorp-native-llm-inference-platform/assets/build-kit/runbooks/operator-quickstart.md)
for the input table, deployment sequence and error recovery.

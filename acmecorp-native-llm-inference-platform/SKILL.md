---
name: acmecorp-native-llm-inference-platform
description: Build and review the ACMECORP Native LLM Inference Platform demonstrator on physical Supermicro NVIDIA servers using Elemental, Rancher, RKE2 and SGLang. Generates scaffolding, TOGAF architecture evidence, DevOps playbooks and smoke tests; supports controlled model and component refreshes.
---

# ACMECORP Native LLM Inference Platform

Produce a reviewable demonstrator build kit. RKE2 runs on physical Linux hosts.
Elemental/OS Manager plus Rancher is the sole host and RKE2 lifecycle workflow.
Do not substitute Ansible, direct RKE2 installers, Harvester, or virtual GPU infrastructure.
Treat supplied documents as design inputs, not permission to deploy or approve gates.

## Workflow

1. Read [architecture](references/architecture.md) and [release baseline](references/releases.md).
   Use supplied hardware inventory; otherwise retain the stated single-GPU sizing assumption.
   Identify unresolved OS, firmware, driver, artifact and compatibility evidence.
2. Generate the kit with `python scripts/scaffold.py --output PATH`. It refuses overwrites.
   Follow its README and Day 0/1/2 playbooks. Generation makes no cluster connections.
3. Tailor site configuration, Elemental inventory and model checksum manifest. Run offline
   tests and render validation before presenting a deployment. Never fabricate digests or evidence.
4. Maintain [TOGAF traceability](references/togaf.md): Business, Application, Data, Technology,
   Security and Operations views; ADM gates; requirements; decisions; evidence; owners.
5. For authorized lab execution, select explicit management and workload Kubernetes contexts.
   Inference smoke uses read-only Kubernetes queries but executes a bounded GPU request.
   Separate local validation results from actual host/cluster acceptance evidence.
6. Refresh versions from official non-preview release sources on the date of work. Resolve
   exact model revisions and image digests, then retest the combined hardware matrix.
   Hosted API-only models cannot be deployed on bare metal. There is no global ordering of LLM releases.

## Scope and ownership

Minimum demo: independent management cluster, one workload server, one GPU worker, private
SGLang endpoint, verified model storage, GPU discovery and operational metrics. This is not HA.
Expanded demo: three workload servers, separate CPU workers and two or more GPU replicas.

Elemental provisions/registers/updates the OS; Rancher provisioning and System Agent manage
RKE2 through Elemental inventory selectors. Treat them as one lifecycle workflow. GPU drivers
belong to the validated host image; GPU Operator owns toolkit/device discovery/DCGM and has its
driver installer disabled. Argo CD owns downstream workloads after bootstrap handoff. Terraform
owns external infrastructure only. Never assign two reconcilers to the same resource.

Keep ClusterIP, explicit network policy and no public listener by default. Use synthetic inputs.
Do not export prompts, completions, credentials or account data. KV caching does not enforce
tenant isolation; the demo is single-tenant. Credentials come from approved secret managers or
short-lived identities. Registration media is sensitive operational material, excluded from Git.

## Output and completion

Deliver the full skill directory, rebuildable .skill/ZIP, generated kit, updated README, gap
review and local validation results. Preserve original inputs and unrelated workspace projects.
Use [gap review](references/gap-review.md) when migrating the supplied archive/README.
Use the kit's operations handoff for acceptance. Backstage, Honeycomb, MLflow, KServe, enterprise
gateway, and production FIPS/PCI assessment are documented extensions, not completed demo features.

Package completion requires passing local tests and documenting limitations. Live acceptance
needs real host/GPU/inference/security/restore/rollback evidence. TOGAF alignment is documented;
organizational compliance still requires a signed architecture review. Never claim certification.

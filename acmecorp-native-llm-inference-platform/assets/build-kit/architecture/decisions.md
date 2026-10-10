# Decisions and transition plan

ADR-001 — **Accepted design constraint (user)**: Elemental/OS Manager + Rancher is the sole
OS/RKE2 lifecycle workflow. Elemental handles registration/images; Rancher/System Agent handles
cluster plans. Ansible and direct host installers are excluded. Consequence: an independent
management plane and its own restore path are prerequisites.

ADR-002 — **Proposed demo sizing**: Qwen3.6-27B BF16, 1x80 GiB GPU, TP=1, context 4096,
concurrency 2, one replica and Recreate. Consequence: downtime during upgrades/faults, no HA or
long-context capability claim. Validate measured memory and quality; owner LLMOps.

ADR-003 — **Proposed storage/security**: independently verified immutable model snapshot,
read-only existing PVC and restricted non-root runtime. No runtime egress or downloads. Resolve
CSI/local-PV details and runtime image compatibility; owner Platform + Security.

ADR-004 — **Proposed access**: private ClusterIP and operator localhost tunnel for synthetic
single-tenant demo. No enterprise gateway, cross-tenant cache, public endpoint or financial action.
Gateway/OIDC/quota requirements block expanded client access; owner Security.

ADR-005 — **Open support decision**: candidate newest upstream versions are not an approved
support intersection. Record OS/driver/firmware/Rancher/Elemental/RKE2/GPU Operator versions,
support URLs, actual test evidence and any downgrade to a supported minor; owner Platform.

Transition work packages: W1 validate management/hardware; W2 enroll physical hosts and RKE2;
W3 GPU/model/runtime; W4 live smoke and monitoring; W5 recovery/handoff. W6 (separate scope)
adds three-server HA, CPU pool, two GPU replicas, private gateway, SLOs and identity. W7 adds
portal/registry/trace export and production governance. Dependencies flow W1 through W5; do not
make Backstage or external telemetry a serving prerequisite.

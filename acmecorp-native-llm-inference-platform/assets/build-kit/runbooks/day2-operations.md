# Day 2 — diagnose, change and recover

**Owner:** Operations, with LLMOps and Platform escalation queues named in handoff.
Start by recording release ID, selected context, symptom, time and change/incident reference.
Do not paste tokens, full pod environments, registration URLs, prompts or completions into tickets.

| Symptom | First checks | Mitigation and escalation |
|---|---|---|
| Pending inference pod | Pod events, bound PVC/node affinity, GPU allocatable, CPU/RAM requests | Fix reviewed placement/capacity; no public exposure workaround; Platform |
| Verify-model init fails | Inventory identity, missing/extra files, PVC permissions, approved hashes | Restore verified snapshot; never bypass verifier; Model owner |
| CUDA/driver failure or GPU disappears | GPU Operator pods, sanitized nvidia-smi, Xid/ECC, kernel/driver tuple | Quarantine under approved maintenance; rebuild through Elemental; Hardware + Platform |
| Empty/truncated canary | Template/revision, reasoning mode, token budget, server error count | Revert serving profile/model; quality review, not loosen test to pass; LLMOps |
| Slow response/OOM | Queueing, HBM, context, active requests, cold/warm state | Reduce admitted work through reviewed profile; no uncontrolled retries; LLMOps |
| Registration/RKE2 provisioning stalls | Correct management context, CRDs, TPM inventory, selectors, Rancher agent and CA trust | Correct source config and reconcile; never create parallel manual install; Platform |
| Missing metrics | Matching pod/namespace labels, service DNS/port, NetworkPolicy, scrape status | Restore config; inference should continue; SRE |
| Rancher unavailable | Existing serving endpoint, management DNS/certs, backup freshness | Freeze lifecycle changes; restore management plane independently; Platform |

## Release and rollback

Retain previous release commit, runtime digest, model snapshot hashes/PVC, image/channel and
signed evidence before any change. Change one layer at a time. Run static and support checks,
preview diff, obtain required change approval, then reconcile. Confirm desired Git commit and
observed runtime digests; run smoke and compare the cold/warm baseline.

For inference regression: stop promotion; revert Git to prior runtime/model/config references;
wait for Argo sync and rollout; rerun smoke and quality cases; record outage and decision. On one
GPU Recreate causes downtime. A previous ConfigMap alone cannot recover deleted model weights.
For host/driver regression: use the tested Elemental image rollback/replacement workflow. Keep
host OS rollback separate from RKE2 datastore recovery. Do not force a Kubernetes downgrade.

## Management and datastore recovery drill

1. Verify off-cluster encrypted management backups, certificates, registry access and required
   decryption material. Record a current restore runbook for the chosen Rancher/Elemental versions.
2. Restore the management plane in an isolated network using the vendor backup/restore procedure.
   Avoid two management planes sending plans to the same hosts. Verify inventory/selectors and
   connections only after ownership is unambiguous.
3. Verify workload etcd snapshots and the original RKE2 server token are retained securely. The
   token is needed to decrypt bootstrap data; snapshots without it are not a proven restore.
4. Restore/rebuild an isolated workload cluster under Rancher-supported recovery; check nodes,
   data identity, model PVC and smoke. Measure RTO and RPO against agreed targets, not examples.
5. Rebuild one GPU worker via Elemental with an approved disk/serial map, preserve authoritative
   model data externally, verify CDI after reboot and repeat inference checks.

A management backup is not a workload etcd backup. A model cache is not its authoritative source.
No automated drain/reset/delete is supplied. Lab acceptance requires an operator to execute and
record the recovery drill; production changes require its own approvals.

## Routine operations

Before demo: check cert expiry, model/runtime digest availability, Ready nodes, GPU health,
free disk, pending updates and smoke. Weekly during use: review driver/vendor advisories,
metrics privacy and backup freshness. Before an upgrade: recheck the supported version tuple,
scan SBOMs, review migrations and prove rollback on the lab hardware. Retain evidence under the
organization's approved retention policy, with named owner and access controls.

# Operator quick start

Run from a fresh generated kit with Python 3.12+ and PowerShell 7+. This kit creates
reviewable configuration; Rancher/Elemental and the approved GitOps owner deploy it.
Use synthetic prompts only. The default topology is one server and one GPU worker.

## 1. Check inputs before touching hosts

```powershell
python scripts/prepare.py --check
if ($LASTEXITCODE -ne 0) { throw 'Resolve the listed inputs before proceeding.' }
```

Initial failure is expected. Obtain real values for these fields:

| File | Operator supplies | Why it matters |
|---|---|---|
| config/elemental.json | Seed image digest, public SSH key, supported RKE2 patch, support evidence | Enrolls hosts under one lifecycle owner |
| config/elemental.json pools | Each host's verified install disk by-id | Incorrect values can erase the wrong disk |
| config/site.json | Runtime digest, GPU hostname, model PVC, release ID, support evidence | Fixes the workload identity and placement |
| config/site.json | Pod Security minor matching RKE2 | Preparation catches minor-version drift |
| config/model-files.json | Approved model ID/revision and every file's SHA-256 | Verifier rejects changed or extra files |

The default version tuple is an upstream stable candidate, not a supported hardware certificate.
Keep the model snapshot pinned. Do not manufacture hashes, evidence references or credentials.
Obtain image digests from approved artifacts; keep secrets and registration URLs outside Git.

## 2. Create a review bundle

```powershell
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed.' }
python scripts/prepare.py --output generated/review-001
if ($LASTEXITCODE -ne 0) { throw 'Bundle preparation failed.' }
```

Both configurations validate before writing. The new directory contains elemental.json,
workload.json and CHECKSUMS.txt. Existing directories are refused. A failed disk write may
leave an incomplete directory: preserve it for diagnosis and choose a new output directory.

## 3. Review and deploy in sequence

1. Follow [Day 0](day0-elemental.md): independent management plane, disk/serial verification,
   backups, supported OS/driver tuple and reviewed host enrollment.
2. Server-dry-run elemental.json using the management context. Resolve errors before the
   authorized owner applies it or attaches boot media. Applying and booting can erase disks.
3. After hosts are Ready, follow [Day 1](day1-deploy-test.md): GPU Operator, tested CDI,
   namespace and existing model PVC, and independently verified model snapshot.
4. Server-dry-run workload.json using the workload context. Review the diff, then let the
   existing GitOps owner deploy the entire bundle. Do not mix Helm, Fleet and Argo ownership.
5. Wait for the deployment and both containers to become Ready. Start the localhost tunnel
   in the [README](../README.md), then run smoke with the same reviewed site and inventory.
6. Run negative network tests, performance and [recovery](day2-operations.md) drills before
   completing the [handoff record](operations-handoff.md).

Monitoring scrapes port 30001, exact GET /metrics only. Inference uses port 30000 through
the authorized localhost tunnel. Update old scrape targets and review additive policies
that could still open 30000. This kit does not supply an enterprise authentication gateway.

## Common failures

| Symptom | Action |
|---|---|
| Python opens Windows Store | Use the full path to an installed Python 3.12+ interpreter |
| Resolve field / exit 2 | Complete the named input using independently reviewed evidence |
| Output exists | Choose a new bundle/evidence directory; do not overwrite review history |
| Model verifier fails | Check the approved snapshot, materialized symlinks, permissions and extra files |
| Pod pending | Check PVC binding, GPU-node affinity, allocatable GPU and requested RAM |
| Model/release smoke fails | Compare Git rollout, pod annotations, checksum init, expected node and PVC |
| Metrics fail after upgrade | Confirm metrics sidecar is Ready, Service exposes 30001 and scraper targets 30001 |
| HTTP check fails | Check tunnel, TLS/auth and server health; total deadline defaults to 60 seconds |

Smoke saves PASS/FAIL names without bodies or tokens. A local test pass is not hardware
acceptance. Preserve prior model/runtime artifacts for rollback; this single-replica demo
has downtime during replacement. No production or public deployment is implied.

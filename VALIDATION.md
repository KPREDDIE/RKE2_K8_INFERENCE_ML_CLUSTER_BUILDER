# Validation record - 9 October 2026

Scope: local build and loopback HTTP tests; no management or workload cluster contacted.
Windows PowerShell; Python 3.13.5 for cached vendor schemas and bundled Python for the
standard-library build checks. Localhost tests require permission to connect to loopback.

| Check | Result |
|---|---|
| Regression suite | 21 PASS |
| Stale model revision with healthy old rollout | Rejected |
| Monitoring ingress policy | Only metrics port 30001 permitted |
| Proxy path guard | Non-metrics paths rejected without upstream request |
| Real HTTP worker | JSON and SSE loopback requests PASS |
| Trickling stream | Hard deadline terminates active request |
| Missing site inputs and Kubernetes-minor mismatch | Fail closed |
| Bundle, scaffold and installer overwrite protection | PASS |
| Generated standalone kit suite | PASS |
| Candidate/default version and model consistency | PASS |
| Python/JSON syntax and skill Markdown links | PASS |
| Cached Kubernetes/Elemental schemas | 12 objects PASS |

Build command: `python tools/build.py --output release/NEW_RELEASE`.
The buildspec enforces validation before packaging. Archive CHECKSUMS.txt verifies transport
integrity, not publisher authenticity. Runtime/media digests and real model hashes remain
site inputs. The old versioned archives are preserved.

The three review findings and residual live checks are recorded in README.md. No live GPU,
network isolation, Rancher admission, recovery or production acceptance has been established.
The schema library emits its existing RefResolver deprecation warning; validation succeeds.

## Historical validation - 5 October 2026


Date: 2026-10-05 (America/Phoenix). Environment: Windows PowerShell, Python 3.13.5.
Scope: local artifact behavior and offline schemas, not a deployed environment.

| Check | Result |
|---|---|
| Skill-creator quick_validate.py | PASS |
| Build-kit unittest suite | 13 tests PASS |
| Generated standalone kit runs its own suite | PASS |
| Scaffold and installer preserve existing destination | PASS |
| Unresolved Elemental/workload input refuses render and writes no output | PASS |
| Python syntax and JSON parsing | PASS |
| Local Markdown links inside the skill | PASS |
| Kubernetes v1.37.1 OpenAPI checks | 6 rendered objects PASS |
| Elemental operator v1.9.2 CRD schema checks | 6 rendered objects PASS |
| Source ZIP / skill archive CRC and member checksums | PASS |
| Extracted source ZIP reproducible rebuild | PASS |

The 13 tests cover unsafe/unresolved renders, model identity/path/hash validation, restricted
network/workload invariants, disjoint Elemental role selectors, empty-node false positives,
TLS/redirect policy, exact canary completion, a fully mocked successful smoke run, failed
cluster/HTTP handling without raw error leakage, and strict runtime inventory with preserved usages.
Mocks are synthetic; none of these tests establishes real inference or physical-host readiness.

## Reproduce

Run `python tools/validate.py`. The standard suite requires no network or Python dependencies.
For the optional schema pass, use `python tools/validate.py --schemas PATH`, with PyYAML 6.0.2
and jsonschema 4.23.0 (versions used here). Place these publicly sourced files in PATH:

- kubernetes-v1.37.1.json from https://raw.githubusercontent.com/kubernetes/kubernetes/v1.37.1/api/openapi-spec/swagger.json
- machineregistrations.yaml from https://raw.githubusercontent.com/rancher/elemental-operator/v1.9.2/config/crd/bases/elemental.cattle.io_machineregistrations.yaml
- seedimages.yaml from https://raw.githubusercontent.com/rancher/elemental-operator/v1.9.2/config/crd/bases/elemental.cattle.io_seedimages.yaml
- machineinventoryselectortemplates.yaml from https://raw.githubusercontent.com/rancher/elemental-operator/v1.9.2/config/crd/bases/elemental.cattle.io_machineinventoryselectortemplates.yaml

Schemas are not included in the release. Kubernetes OpenAPI v2's int-or-string format is normalized
to its JSON union for validation. The library emits a RefResolver deprecation warning; this does
not affect the validation result. Vendor schema checks do not validate every unknown field,
Rancher admission behavior, policies, runtime compatibility or platform support.

Schema content SHA-256:
- `kubernetes-v1.37.1.json`: `465276aedf437726de5a6ed23a41b86d78bb0d347edf251a755ae26a93cdd8a6`
- `machineinventoryselectortemplates.yaml`: `59877588c77919fa3285e5e397c92a1eca2ca3179885e290916faac742ebbb20`
- `machineregistrations.yaml`: `ca0b75b86c3d20d8b14ddc654989c83762b7d7b2aa480907e6361bcc1f27aab9`
- `seedimages.yaml`: `bde73ffe576ad8b604c694add54c08b0ecf3613efd3d5724b9e60ea3dda0d6c6`

## Live checks not performed

Rancher Cluster CRD/admission server dry-run; management restore and inventory enrollment;
actual OS/kernel/firmware/driver/GPU compatibility; vendor stable-chart resolution and signatures;
SGLang image security/non-root startup; model artifact provenance and file hashes; PVC readiness;
CUDA/CDI and GPU memory; non-streaming/streaming inference; network/RBAC negative tests;
Prometheus/DCGM/OTel deployment and privacy; quality/safety; latency/throughput; worker rebuild;
etcd restore; rollback and independent human acceptance.

The candidate pins therefore remain unapproved integration inputs. Null site values are deliberate
release gates, not placeholder evidence. No live cloud, cluster, BMC, PXE or model endpoint was changed.

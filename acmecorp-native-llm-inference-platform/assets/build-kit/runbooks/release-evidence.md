# Release evidence and supply-chain playbook

Owner: Release + Security. A declared version list is not a complete SBOM. The original archive's
SBOM is replaced by explicit candidate metadata and a strict runtime inventory helper.

For one release ID retain: source commit, rendered manifest hashes, architecture decisions,
Rancher/Elemental chart versions and package digests, seed/host image, BIOS/BMC/NIC/GPU firmware,
OS/kernel/packages, NVIDIA driver/CUDA, RKE2 binary and images, every deployed container digest,
model/tokenizer/template/license hashes, scan database version, VEX/exception disposition,
actual test reports, prior rollback target and human decisions.

Use approved Syft/CycloneDX tooling to generate host/container SBOMs. Add a model BOM from the
verified file inventory and compose a CycloneDX release BOM with unique bom-ref identifiers
and complete dependency edges. Validate against the chosen CycloneDX JSON schema and reject
orphaned references or silent edge loss. This kit does not fabricate those scans or signatures.
Sign through the organization's managed signing identity and verify with a separate identity.

For an authorized runtime observation, use a private temporary directory for kubectl pod JSON:

```powershell
$WorkloadContext = Read-Host 'Approved workload context'
$PrivatePodFile = Read-Host 'Temporary private pod JSON path outside Git'
kubectl --context $WorkloadContext -n acmecorp-inference get pods -o json | Set-Content -LiteralPath $PrivatePodFile -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw 'Pod inventory query failed' }
python scripts/runtime_inventory.py --pods-json $PrivatePodFile --namespace acmecorp-inference --output evidence/runtime-001.json
```

Raw Pod specs can contain sensitive configuration: restrict access and remove the temporary
file according to policy after processing. The helper retains only image identities and usage,
rejects empty/incomplete inventories or non-digest image IDs, and does not call the cluster itself.
It is intentionally called an inventory, not a schema-validated or complete SBOM.

Compare observed image IDs with resolved platform-specific manifests as well as OCI multiarch
index digests; an index and its selected platform manifest are different digests. Record this
mapping before interpreting a runtime mismatch. The baseline smoke expects a platform-specific
runtime image digest for linux/amd64 so that equality is direct.

Block release on unresolved compatibility, missing artifact identities, failed provenance,
unaccepted vulnerabilities, failed live validation, missing rollback, content leakage or absent
required review. Demo evidence packaging is not production promotion. Preserve registration URLs,
seed media and all credentials outside source and release ZIPs.

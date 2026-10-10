# Day 0 — hardware, management and Elemental readiness

**Owner:** Platform engineer. **Reviewers:** Hardware, Network, Security and Architecture.
**Entry:** approved lab scope, physical access and change authority, independent Rancher management
cluster, backup owner and verified inventory. This document does not authorize disk erasure.
**Exit:** signed compatibility record, reviewed renders, recoverable management backup and matched host identities.

## 1. Inventory and support

Complete architecture/site-inventory.csv for each serial number. Confirm Supermicro server SKU,
BIOS/BMC, GPU SKU/VRAM, NIC, NVMe serial/by-id, TPM 2.0, UEFI/Secure Boot policy, racks, power,
VLANs, MTU and console access. Use vendor-supported firmware; never pick firmware by family name
alone. Capture vendor compatibility URLs and actual release artifacts in the evidence store.

Record Rancher edition/entitlement and version, Elemental operator/CRD chart, seed/OS image,
RKE2, kernel, NVIDIA driver, CUDA userspace, GPU Operator and containerd/CDI compatibility.
The supplied newest-upstream candidates may not be a supported intersection. No compatible
SLE Micro/driver evidence means stop image freeze, not install drivers manually afterwards.
Build the driver into the validated Elemental OS image or choose a vendor-supported image route
through an ADR; keep GPU Operator's driver installer disabled for this profile.

## 2. Management plane

The management cluster must already have independent storage, DNS, trusted certificates, IAM,
registry access and a tested restore route. Pin Rancher and Elemental charts/images from the
appropriate vendor channel. Do not assume operator application and chart versions are equal.
Install/upgrade CRDs before their controllers under that cluster's approved bootstrap procedure.
Use a distinct management context:

```powershell
$ManagementContext = Read-Host 'Approved management context'
kubectl --context $ManagementContext get crd machineregistrations.elemental.cattle.io seedimages.elemental.cattle.io machineinventoryselectortemplates.elemental.cattle.io
kubectl --context $ManagementContext -n cattle-elemental-system get deployments,pods
kubectl --context $ManagementContext -n cattle-system get deployments,pods
```

Review least-privilege grants: CRD/operator installation is cluster-scoped; routine registration
and selector operations belong in fleet-default. Do not grant developers cluster-admin merely
to run inference smoke. Inspect CRD schemas in the installed version before applying generated JSON.
Back up Rancher/Elemental configuration, management datastore and required encryption material.
Registration URLs and media can enroll machines: keep them out of logs, tickets, Git and ZIPs.

## 3. Register and boot physical hosts

Populate config/elemental.json. Each pool's install_device must be independently confirmed against
that host's console and serial number. The base profile has one machine per pool. For multiple
hosts with different by-id devices, use per-host registrations/media and extend selectors; do not
reuse a disk path from another host. Match labels include both cluster and role to prevent
unintended enrollment. Review TPM identity and duplicate inventory records before selection.

```powershell
python scripts/render.py elemental --output generated/elemental-001.json
kubectl --context $ManagementContext apply --dry-run=server -f generated/elemental-001.json
kubectl --context $ManagementContext diff -f generated/elemental-001.json
```

A diff return code of 1 means changes were found; greater than 1 is an error. Server dry-run and
diff contact the API but do not install hosts. Actual apply plus booting installation media can
lead to disk overwrite. Execute only under the approved lab provisioning change, after the
reviewer checks the concrete disk/host mapping and backup. No generated shell applies resources.

The default boot path is Elemental-built ISO through restricted Supermicro BMC virtual media.
Verify media checksum and CA trust; attach only to the intended serial number and use one-time
boot. Observe registration, OS install, reboot and Rancher provisioning. Remove virtual media
and revoke registration access when the enrollment window ends. Do not capture registration URLs.

For a PXE site, first establish a vendor-supported network-boot integration for the selected
Elemental release. The standard SeedImage API documents ISO and RAW, not a native PXE output.
Do not infer that a generic iPXE recipe is supported. Reserve DHCP by approved NIC MAC, isolate provisioning VLAN, verify signed boot chain,
serve artifacts from restricted trusted endpoints, and expire enrollment. An ISO cannot simply
be used as an iPXE kernel. This kit deliberately supplies no environment-specific DHCP/TFTP
configuration or destructive BMC automation.

## 4. RKE2 onboarding and stop conditions

Elemental creates MachineInventory; selector templates bind server/GPU roles; Rancher System
Agent applies the selected RKE2 version and config. Do not run get.rke2.io or a parallel OS updater.
Review the generated server role: it has control-plane/etcd, not worker. Verify add-on tolerations
and provide a CPU worker if the site's policies prohibit system services on the demo server.

Stop for unexpected disk mapping, untrusted cert, wrong TPM/serial, unsupported driver/kernel,
version unavailable in Rancher, failed media verification, selector overlap or absent recovery
material. Preserve diagnostics with credentials redacted; route hardware to Hardware Ops,
registration to Platform Ops, and trust/identity problems to Security. Restart from the reviewed
media/config after resolving the cause, not from ad-hoc host edits.

## Seed verification

Wait for SeedImageReady=True and verify the checksum from the trusted management endpoint,
not just that a builder Pod is Running. ISO media is explicitly x86_64 and expires after 60 minutes
in the renderer. Retain required approved media in a private operational store, not the source ZIP.
Use the [SeedImage reference](https://elemental.docs.rancher.com/seedimage-reference/) for the
selected release and certificate-validated downloads.

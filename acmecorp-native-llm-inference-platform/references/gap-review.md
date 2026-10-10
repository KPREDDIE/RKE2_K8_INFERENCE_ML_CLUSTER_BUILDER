# Input review and resolved gaps

Inputs: acmecorp-native-llm-inference-platform.skill (ZIP skill directory) and HARVESTER PXE.md
(a README, despite its filename). They were read as source material. Original files are preserved.

| Finding | Refactor |
|---|---|
| Skill assigned Ansible/image pipeline host ownership; README mandated Elemental | User selected Elemental. Elemental OS + Rancher/System Agent RKE2 ownership is consistent throughout |
| README promised missing operations-handoff, installer and folder-hierarchy files | Self-contained kit and actual handoff, scaffold, installer and package tooling; only real links |
| Baseline had version lists but no selected LLM or immutable model revision | Verified Qwen3.6-27B revision plus checksum-inventory gate |
| No deployable scaffolding in archive | Renderers for Elemental registration/seed/selectors/cluster and restricted SGLang workload |
| API lifecycle statements blurred Elemental and Rancher responsibilities | Explicit owner map and independent management-plane prerequisite |
| Empty nodes / missing Ready condition could pass original smoke | Both now fail; selected GPU and runtime digest checked |
| Original completion passed for any nonempty output | Exact finished synthetic canary plus streaming completion |
| Original scripts required bash/Linux-specific date and /proc UUID; missing command checks | Python stdlib helpers, cross-platform local execution and bounded subprocess/network calls |
| Original smoke sent auth to arbitrary metrics endpoint and allowed unencrypted remote HTTP | Same-origin metrics, TLS for remote access, no redirects, token never in argv or evidence |
| Original SBOM accepted image IDs without a digest, discarded duplicate dependency edges; top-level type platform invalid in CycloneDX 1.6 | New strict observed-image inventory; full SBOM construction/schema validation remains an explicit release stage |
| Latest versions conflated with support/readiness | Dated source record, candidate status and unresolved support matrix |
| Production breadth obscured demo scope | Minimum functional profile; HA, FIPS, enterprise gateway and optional services explicitly deferred |
| TOGAF described roles but no concrete traceability kit | ADM map, requirements CSV, ADRs, compliance review and handoff templates |

## Outstanding validation

No physical host access or cluster deployment was authorized/executed. Support intersection,
image digests, signed media, disk inventory, model-file hashes, non-root runtime behavior,
CRD server validation, performance, network-policy enforcement, telemetry privacy, restore and
rollback require site evidence. Templates do not confer PCI compliance, FIPS validation, ATO,
model-safety approval or an architecture-board decision.

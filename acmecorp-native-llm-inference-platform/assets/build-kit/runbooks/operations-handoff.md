# Operations acceptance record

Release ID: unassigned | Environment: lab | Decision: NOT REVIEWED
Accountable Operations owner / support queue / backup owner / LLMOps queue / Security queue:
assign before live acceptance. An unnamed role is not a working escalation contact.

| Required handoff | Evidence/reference | Reviewer | Status |
|---|---|---|---|
| Hardware/disk map and supported version matrix | not supplied | Platform | Open |
| Architecture/ADRs/requirements and deviations | architecture/ | Architecture | Draft |
| Identity, RBAC, registry and secret access | not supplied | Security | Open |
| Host/media/model/runtime provenance and SBOM scans | not supplied | Security + Model owner | Open |
| Live smoke, performance, quality and privacy reports | not run | LLMOps + SRE | Open |
| Dashboards/alerts or documented demo monitoring procedure | not run | SRE | Open |
| Management restore, etcd restore, worker rebuild and rollback drill | not run | Platform | Open |
| Known risks: non-HA, single tenant, optional extensions | architecture/decisions.md | Sponsor | Pending acceptance |
| Alternate engineer executes Day 0/1/2 without author | not run | Operations | Open |

Acceptance requires dated reviewer identities, evidence hashes, exceptions with expiry and a
named rollback authority. Status can be accept, conditional accept with documented residual
risk, or reject. Never prefill approval. A package test pass does not fill this record.

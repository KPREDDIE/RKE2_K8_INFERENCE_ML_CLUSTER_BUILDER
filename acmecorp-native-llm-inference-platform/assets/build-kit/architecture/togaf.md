# TOGAF alignment and architecture review

Use the [TOGAF Standard, 10th Edition](https://www.opengroup.org/togaf) as the method reference.
This kit tailors ADM deliverables to a demonstrator. It is not a TOGAF-certified product.
Security and Operations are cross-cutting views alongside Business, Application, Data and Technology.
The architecture board must decide organizational compliance from evidence, not this text.

| ADM phase | Demonstrator deliverable | Accountable owner | Gate evidence |
|---|---|---|---|
| Preliminary | Scope, principles, lifecycle owner map, repository | Enterprise Architect | Governance approval |
| A Vision | Repeatable private demo and stakeholder outcomes | Sponsor | Agreed demo acceptance |
| B Business | Engineer build/release/support journey | Product owner | RACI and handoff |
| C Data/Application | Model provenance, APIs, telemetry boundaries | Data/App architect | Data flow and retention review |
| D Technology | Elemental/Rancher/RKE2/GPU topology | Platform architect | Hardware support matrix |
| E Opportunities/Solutions | Minimum demo to HA transition | Architecture board | Work packages and dependencies |
| F Migration | Day 0/1/2 sequence and rollback | Release manager | Change plan and rollback target |
| G Implementation Governance | Requirements to manifests/tests/evidence | Platform + Security | Compliance review decision |
| H Change Management | Version refresh, incident and capacity learning | Operations owner | Change/ADR history |
| Continuous requirements | IDs, owners, tests, results, exceptions | Requirements owner | No unowned gaps |

The generated kit includes architecture/requirements.csv, decisions.md, compliance-review.md,
and site-inventory.csv. Each requirement names an implementation, test and evidence path.
The evidence field is initially not-run; planned tests are not passed tests. Record a real evidence
URI/hash, reviewer and decision before moving to accepted. Exceptions require risk, scope, owner,
expiry and remediation; they must not disappear when the release ID changes.

ABB to SBB mapping: host lifecycle -> Elemental/OS Manager; cluster -> Rancher/RKE2; GPU execution
-> host driver plus GPU Operator; inference API -> SGLang; model provenance -> immutable mirror
and verified PVC; operations -> metrics and playbooks; governance -> Git plus review evidence.

Architecture Contract: the implementer delivers the stated scope and evidence; Operations
accepts only tested procedures; Security reviews boundaries; Sponsor accepts demo residual risk.
An author cannot independently approve their own production promotion. No approvals are prefilled.

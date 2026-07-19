# Role and Permission Matrix

Legend: **E** edit, **V** view, **S** scoped view/edit based on division/project membership, **R** restricted/field-level, **—** no routine access.

| Role | Executive / Division | Demand | Assessment | Decision | Project / RAID | Resource | Financial | Benefits | Import / RTM | Audit / Admin |
|---|---|---|---|---|---|---|---|---|---|---|
| DDC5I Senior Leader | V enterprise | V | V | E Gate 4 | V | V summary | V summary | V | V RTM | — |
| Enterprise Portfolio Owner | V enterprise | E | V/E recommendation | V | E portfolio | V | V summary | V | V RTM | V governance |
| PMO / Portfolio Manager | V enterprise | E | E | V | E | V | V summary | V | E imports/RTM | V audit |
| Division Chief | S | S/E | S/V | V | S/V | S/V | S/V summary | S/V | — | — |
| Division Portfolio Manager | S | S/E | S/E | V | S/E | S/V | S/V summary | S/V | E import if authorized | — |
| Demand Sponsor / Requester | S | S/E own | V own | V own | V linked | — | V ROM | V linked | — | — |
| Assessor | S | S/V | S/E | V | V evidence | V summary | V summary | V | — | — |
| Approval Authority | V | V | V | E | V | V summary | V summary | V | — | — |
| Project Manager | S | S/V | V | V | S/E | S/V | S/V | S/E | — | — |
| Team Member | S | S/V | — | V linked | S/E assigned | — | — | V linked | — | — |
| Resource Manager | V summary | V skills | V feasibility | V implications | V assignments | E | R | V | — | — |
| Financial Manager | V summary | V cost | V value | V implications | V | R | E/R | V | — | — |
| Benefits Owner | V summary | V benefits | V value | V | V | — | V summary | E | — | — |
| Data Steward | V | V | V | V | V | V | V summary | V | E RTM/import/reference | V quality |
| Security / Privacy Reviewer | V permitted | R | R | V | R | R | R | R | V RTM | V audit |
| Auditor | V | V | V | V | V | V | V permitted | V | V RTM | V audit; no business edits |
| Platform Administrator | V/E technical | E local demo | E | E local demo | E local demo | E local demo | E local demo | E local demo | E | E |

## Enforcement layers

1. **Authentication:** signed local demonstration session.
2. **Role:** route/action requires one or more roles.
3. **Organization:** non-enterprise users are limited to their division.
4. **Record:** project and demand access is resolved server-side by canonical ID.
5. **Sensitivity:** restricted or sensitive records require explicit permission.
6. **Field:** sensitive rate/personnel data is excluded from general dashboards; full field-level policy is roadmap work.
7. **Separation of duties:** auditor is read-only; additional submitter/approver conflict warnings are roadmap/policy work.
8. **Delegation:** model fields exist for acting user and expiry; complete delegation workflow is planned.

## Role assignment notes

Users may hold multiple roles. In production, role claims should be provisioned from approved identity groups and supplemented by application-specific organization/project assignments. Enterprise roles must be tightly controlled because they bypass division scope. Sensitive access must be independent of ordinary business roles.

## Current limitations

The UI does not yet provide full user/role administration, project-membership grants, field-level policy configuration, delegation approval, or separation-of-duties conflict resolution. These requirements are recorded as partial/planned/governance-dependent in the RTM.

## v0.5.0 permission additions

| Capability | Senior Leader | Enterprise Portfolio Owner | PMO | Division Chief / Portfolio Manager | Resource Manager | Financial Manager | Data Steward | Auditor | Administrator |
|---|---|---|---|---|---|---|---|---|---|
| View portfolio reviews | Yes | Yes | Yes | Scoped | No by default | No by default | No by default | Read if assigned role permits | Yes |
| Create/manage review | Yes | Yes | Yes | Scoped | No | No | No | No | Yes |
| Decide review item | Yes/authority | Yes | Yes | Scoped authority | No | No | No | No | Yes |
| View integrations/ownership | No by default | No by default | Yes | No | No | No | Yes | Read | Yes |
| Configure connection/ownership | No | No | Limited operation | No | No | No | Health/sync operation | No | Yes |
| Submit resource request | Permitted through portfolio roles | Yes | Yes | Scoped | Yes | No | No | Read only | Yes |
| Decide resource request | No by default | Yes | Yes | Scoped | Yes | No | No | Read only | Yes |
| Add financial transaction | No | Yes | Yes | No by default | No | Yes | No | Read only | Yes |
| Create/calculate scenario | Yes | Yes | Yes | Scoped | Supporting role only | Supporting role only | No | Read only | Yes |
| Approve/apply scenario | Approval role | Yes | Yes | Scoped approval where authorized | No | No | No | No | Yes |
| Run/update data-quality scan | View | No by default | Yes | No by default | No | No | Yes | Read | Yes |
| Generate report pack | View/approve | Generate/approve | Generate | No by default | No | No | Generate | Read | Yes |
| Create/update local user | No | No | No | No | No | No | No | No | Yes |
| Create delegation registry record | No | No | No | No | No | No | No | Read | Yes |

Server-side checks remain authoritative. Division/sensitive/project scope continues to restrict records even when a role grants access to the module. Delegations do not yet augment these checks in v0.5.0.


## v0.7.0 Division Briefing & Review permissions

| Capability | Senior Leader | Enterprise Portfolio Owner | PMO | Division Chief | Division Portfolio Manager | Supporting Manager / Contributor | Auditor | Administrator |
|---|---|---|---|---|---|---|---|---|
| View enterprise/division briefings | Enterprise | Enterprise | Enterprise | Scoped division | Scoped division | Only when existing review/scope access permits | Read permitted records | Yes |
| Create a division briefing | Yes | Yes | Yes | Scoped | Scoped | No | No | Yes |
| Prepare sections and refresh source summaries | Yes | Yes | Yes | Scoped | Scoped | Assigned contributors when their existing role permits review editing | No | Yes |
| Submit for division approval | Yes | Yes | Yes | Scoped | Scoped | No | No | Yes |
| Approve / return a division briefing | Yes | Yes | Yes | Scoped authority | Scoped authority | No | No | Yes |
| Start/facilitate live review | Yes | Yes | Yes | Scoped | Scoped | No by default | No | Yes |
| Ask questions / add review notes | Yes | Yes | Yes | Scoped | Scoped | Permitted participants with review access | Read | Yes |
| Respond to assigned question | Yes | Yes | Yes | Scoped | Scoped | Assigned user | Read | Yes |
| Create / resolve change request | Yes | Yes | Yes | Scoped | Scoped | Assigned owner or permitted facilitator/editor | Read | Yes |
| Record actions and decisions | Authority-dependent | Yes | Yes | Scoped authority | Scoped authority | No by default | Read | Yes |
| Complete a briefing | Yes | Yes | Yes | Scoped authority | Scoped authority | No | No | Yes |

All briefing operations continue to use server-side role, organization, record, and sensitivity checks. A briefing snapshot does not expand access to restricted source records; the live workspace presents only information the current user is permitted to read.

## v0.7.5 Division Profile permissions

| Action | Admin | PMO | Enterprise Portfolio Owner | Data Steward | Division Chief | Division Portfolio Manager | Senior Leader | Auditor | Other roles |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| View accessible division profile | Yes | Yes | Yes | Yes | Scoped | Scoped | Yes | Yes | Scoped by existing organization rules |
| Export accessible JSON/CSV package | Yes | Yes | Yes | Yes | Scoped | Scoped | Yes | Yes | Scoped by existing organization rules |
| Edit division profile | Yes | Yes | Yes | Yes | Scoped | Scoped | No | No | No |
| Import and publish profile JSON/CSV | Yes | Yes | Yes | Yes | Scoped | Scoped | No | No | No |
| Change stable division code or ID | No | No | No | No | No | No | No | No | No |

Profile edits and imports create audit events. Export operations also record format and schema-version evidence.

## v0.7.6 Travel & Engagement permissions

| Capability | Traveler / Requester | Division Portfolio Manager | Division Chief | PMO / Enterprise Owner | Data Steward | Senior Leader | Auditor | Security Reviewer | Admin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| View accessible travel metadata | Yes | Division | Division | Enterprise | Enterprise | Enterprise | Read only | Enterprise | Enterprise |
| View sensitive report narrative | Only when authorized | Division + sensitivity | Division + sensitivity | Sensitivity required | Sensitivity required | Sensitivity required | Sensitivity required | Yes | Yes |
| Import travel requests / reports | No | Division | No | Yes | Yes | No | No | No | Yes |
| Confirm report/request match | No | Division | Division | Yes | Yes | No | No | Review | Yes |
| Review trip-report outcomes | Own/assigned future extension | Division | Division | Yes | Steward support | Read | Read only | Security review | Yes |
| Promote outcome to action/risk/decision | No | Division | Division | Yes | No | No | No | No | Yes |
| Export accessible travel CSV | Accessible scope | Division | Division | Enterprise | Enterprise | Enterprise | Read scope | Enterprise | Enterprise |
| View provenance and audit | Own/basic | Division | Division | Enterprise | Enterprise | Enterprise | Yes | Yes | Yes |

Server-side authorization remains authoritative. Hiding a UI control is not an authorization boundary.

# Bizops (`bizops`)

Business operations: setup/upgrade flows, local-economy track, order planner with mold-ladder reuse.

**Kind:** polari-app · **agent tier:** member · **requires:** supplychain

## Objects

`BizOpsAPI`, `BusinessProfile`, `BusinessRiskNote`, `BusinessStageDefinition`, `BusinessUpgradeStep`, `ComplianceRecord`, `ComplianceRequirement`, `LocalEconomyMilestone`, `MarketSessionRecord`, `PartnershipAgreement`, `ProcessWorkflowDefinition`, `ProductOrder`, `ProductionRunRecord`, `QualityCheckDefinition`, `QualityCheckRecord`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/bizops/BusinessProfile.py`, `objects/bizops/BusinessRiskNote.py`, `objects/bizops/BusinessStageDefinition.py`, `objects/bizops/BusinessUpgradeStep.py`, `objects/bizops/ComplianceRecord.py`, `objects/bizops/ComplianceRequirement.py`, `objects/bizops/LocalEconomyMilestone.py`, `objects/bizops/MarketSessionRecord.py`, `objects/bizops/PartnershipAgreement.py`, `objects/bizops/ProcessWorkflowDefinition.py`, `objects/bizops/ProductOrder.py`, `objects/bizops/ProductionRunRecord.py`, … (3 more)
- **basis** — `bizops_basis.py`
- **api** — `bizops_api.py`
- **seed** — `bizops_seed.py`
- **custom** — `custom/bizops_compliance.py`, `custom/bizops_deals.py`, `custom/bizops_flows.py`, `custom/bizops_guide.py`, `custom/bizops_planner.py`
- **selftests** — `bizops_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest bizops        # in the running backend
PYTHONPATH=.:modules python3 -m bizops.bizops_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform bizops`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

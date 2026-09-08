# Bizops (`bizops`)

Business operations: setup/upgrade flows, local-economy track, order planner with mold-ladder reuse.

**Kind:** polari-app · **agent tier:** member · **requires:** supplychain

## Objects

`BizOpsAPI`, `BusinessProfile`, `BusinessRiskNote`, `BusinessStageDefinition`, `BusinessUpgradeStep`, `ComplianceRecord`, `ComplianceRequirement`, `LocalEconomyMilestone`, `MarketSessionRecord`, `PartnershipAgreement`, `ProcessWorkflowDefinition`, `ProductOrder`, `ProductionRunRecord`, `QualityCheckDefinition`, `QualityCheckRecord`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `bizops_basis.py`
- **api** — `bizops_api.py`
- **seed** — `bizops_seed.py`
- **custom** — `custom/bizops_compliance.py`, `custom/bizops_deals.py`, `custom/bizops_flows.py`, `custom/bizops_guide.py`, `custom/bizops_planner.py`
- **selftests** — `bizops_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest bizops        # in the running backend
PYTHONPATH=.:modules python3 -m bizops.bizops_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform bizops`

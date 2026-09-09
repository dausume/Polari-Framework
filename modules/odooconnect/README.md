# Odooconnect (`odooconnect`)

Odoo ERP connector: JSON-RPC client with sim/ops write guards, instance configs, /api/odoo status.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`BusinessScenarioDefinition`, `OdooConnectAPI`, `OdooInstanceConfig`, `OdooModelBinding`, `OdooSyncReceipt`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/odoo/OdooInstanceConfig.py`, `objects/odoo/_shared.py`, `objects/odoo_bindings/OdooModelBinding.py`, `objects/odoo_bindings/OdooSyncReceipt.py`, `objects/odoo_bindings/_shared.py`, `objects/odoo_scenarios/BusinessScenarioDefinition.py`, `objects/odoo_scenarios/_shared.py`
- **basis** — `odoo_basis.py`, `odoo_bindings_basis.py`, `odoo_scenarios_basis.py`
- **api** — `odoo_api.py`
- **seed** — `odoo_seed.py`
- **custom** — `custom/odoo_analysis.py`, `custom/odoo_client.py`, `custom/odoo_orders.py`, `custom/odoo_scenario_engine.py`, `custom/odoo_sync.py`, `custom/stub_odoo.py`
- **selftests** — `odoo_orders_selftest.py`, `odoo_scenarios_selftest.py`, `odoo_selftest.py`, `odoo_sync_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest odooconnect        # in the running backend
PYTHONPATH=.:modules python3 -m odooconnect.odoo_orders_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform odooconnect`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

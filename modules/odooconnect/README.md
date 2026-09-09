# Odooconnect (`odooconnect`)

Odoo ERP connector: JSON-RPC client with sim/ops write guards, instance configs, /api/odoo status.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`BusinessScenarioDefinition`, `OdooConnectAPI`, `OdooInstanceConfig`, `OdooModelBinding`, `OdooSyncReceipt`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `odoo_basis.py`
- **api** — `odoo_api.py`
- **seed** — `odoo_seed.py`
- **selftests** — `selftest_odoo.py`, `selftest_odoo_orders.py`, `selftest_odoo_scenarios.py`, `selftest_odoo_sync.py`
- **other** — `odoo_analysis.py`, `odoo_bindings.py`, `odoo_client.py`, `odoo_orders.py`, `odoo_scenario_engine.py`, `odoo_scenarios.py`, `odoo_sync.py`, `stub_odoo.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest odooconnect        # in the running backend
PYTHONPATH=.:modules python3 -m odooconnect.odoo_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform odooconnect`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

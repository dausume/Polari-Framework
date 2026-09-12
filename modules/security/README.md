# Security (`security`)

The App / Network / OS security taxonomy, the controls as rows, and three security topology views with reach simulations

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`SecurityAPI`, `SecurityRecord`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/security/SecurityRecord.py`
- **basis** — `security_basis.py`
- **api** — `security_api.py`
- **endpoints** — `security_endpoints.py`
- **seed** — `security_seed.py`
- **page** — `security_page.py`
- **selftests** — `security_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `security.security_page:SEED_SECURITY_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest security        # in the running backend
PYTHONPATH=.:modules python3 -m security.security_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform security`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

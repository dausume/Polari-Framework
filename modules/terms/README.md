# Terms (`terms`)

Terms of service: versioned documents (global or per app) and the append-only acceptance ledger

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`TermsAPI`, `TermsAcceptance`, `TermsDocument`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/terms/TermsAcceptance.py`, `objects/terms/TermsDocument.py`, `objects/terms/_shared.py`
- **basis** — `terms_basis.py`
- **api** — `terms_api.py`
- **seed** — `terms_seed.py`
- **page** — `terms_page.py`
- **selftests** — `terms_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `terms.terms_page:SEED_TERMS_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest terms        # in the running backend
PYTHONPATH=.:modules python3 -m terms.terms_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform terms`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

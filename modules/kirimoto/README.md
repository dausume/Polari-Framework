# Kirimoto (`kirimoto`)

@module kirimoto

**Kind:** isle-app · **agent tier:** member · **requires:** islemesh

## Objects

`KirimotoAPI`, `SlicerInstance`, `SlicerProfile`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `kirimoto_basis.py`
- **api** — `kirimoto_api.py`
- **page** — `kirimoto_page.py`
- **custom** — `custom/build_image.py`
- **selftests** — `kirimoto_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `kirimoto.kirimoto_page:SEED_KIRIMOTO_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest kirimoto        # in the running backend
PYTHONPATH=.:modules python3 -m kirimoto.kirimoto_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform kirimoto`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

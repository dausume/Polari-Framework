# Xr (`xr`)

XR settings cascade + interface variants. Moves in wave 4; core still imports it statically (drop refuses).

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`XrAPI`, `XrGlobalSettings`, `XrInterfaceVariant`, `XrTypeDefault`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `xr_settings_basis.py`
- **api** — `xr_api.py`
- **custom** — `custom/xr_resolution.py`
- **selftests** — `xr_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest xr        # in the running backend
PYTHONPATH=.:modules python3 -m xr.xr_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform xr`

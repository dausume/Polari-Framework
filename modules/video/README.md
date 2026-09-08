# Video (`video`)

_No description in the registry yet._

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`VideoAPI`, `VideoAsset`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `video_basis.py`
- **api** — `video_api.py`
- **custom** — `custom/video_conversion.py`
- **selftests** — `video_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest video        # in the running backend
PYTHONPATH=.:modules python3 -m video.video_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform video`

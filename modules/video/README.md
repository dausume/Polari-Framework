# Video (`video`)

Video assets: upload, conversion (webm/mp4/poster/HLS) and adaptive delivery rows — a Polari feature module that was never registered until sap-1 (2026-09-08).

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`VideoAPI`, `VideoAsset`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/video/VideoAsset.py`, `objects/video/_shared.py`
- **basis** — `video_basis.py`
- **api** — `video_api.py`
- **custom** — `custom/video_conversion.py`
- **selftests** — `video_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest video        # in the running backend
PYTHONPATH=.:modules python3 -m video.video_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform video`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

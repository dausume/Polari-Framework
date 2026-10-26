# Instruments (`instruments`)

Bench instruments as rows: oscilloscope models with cited specs (channels, bandwidth, sample rate, depth, bits, LXI/SCPI transports), reachable endpoints typed at runtime, channel settings, and the CANONICAL WaveformCapture record (the IEEE 488.2 block kept verbatim plus the vendor preamble fields) that both the Agilent and Tektronix command lineages map onto. A DHO804 emulator (an SCPI server) feeds 4-channel captures from synthesised, replayed or device-derived signals so the same client, record and chart are proven before a real instrument is on the bench.

**Kind:** library · **agent tier:** member · **requires:** board

## Objects

`Instrument`, `InstrumentEndpoint`, `InstrumentsAPI`, `ScopeChannel`, `WaveformCapture`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/instruments/Instrument.py`, `objects/instruments/InstrumentEndpoint.py`, `objects/instruments/ScopeChannel.py`, `objects/instruments/WaveformCapture.py`
- **basis** — `instruments_basis.py`
- **api** — `instruments_api.py`
- **endpoints** — `instruments_endpoints.py`
- **seed** — `instruments_seed.py`
- **page** — `instruments_page.py`
- **custom** — `custom/captures.py`, `custom/catalog.py`, `custom/client.py`, `custom/device_feed.py`, `custom/emulator.py`, `custom/lineage.py`, `custom/scpi.py`, `custom/sources.py`
- **selftests** — `instruments_capture_selftest.py`, `instruments_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `instruments.instruments_page:SEED_INSTRUMENTS_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest instruments        # in the running backend
PYTHONPATH=.:modules python3 -m instruments.instruments_capture_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform instruments`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

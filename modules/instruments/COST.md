# instruments — measured cost (the cost rule)

Every number here was MEASURED on pol-core (Intel Core i5-4590 @ 3.30 GHz, 4 cpus, 16 GB, kernel 6.8) on 2026-10-26, osc-5
(OSCILLOSCOPE_PLAN.md §3f). The rows that carry them: `ModuleResourceProfile prf-scope-engines-resource-profile`
(`resources/profile_seed.py`) and the worker's `/capability` `resources` block (`polari-rf-node/prf-scope-engines/cost.json`, also `GET /cost`).

## The worker image `prf-scope-engines:trixie`

| what | measured | how |
|---|---|---|
| image size | **177.8 MB** (`sha256:20e3e43c…`; base `debian:trixie-slim@sha256:a99cfc51…` + python3 3.13.5, python3-numpy, python3-falcon, gunicorn) | `docker image inspect` |
| build time | **20.1 s** (`prf-scope-engines/build.sh`: vendor staging + `docker build`, base already local, apt downloads included) | `time` |
| worker process, idle (gunicorn, one emulator started) | **41.1 MB** resident | `/system-info` process block |
| worker after one 4-channel × 250,000-point capture | 55.3 MB resident; `docker stats` 48.2 MiB, 0.03 % CPU idle | same + `docker stats` |
| one 4-channel × 250,000-point capture (WORD, 2.0 MB over SCPI) | **0.384 s** wall through the container's published port | `ScopeClient.capture` timed |
| compose `mem_limit` | 256 MB | — |

## The emulator in-process (the local rung; the same code the worker vendors)

| what | measured | how |
|---|---|---|
| acquire 4 channels × 250,000 points (synth sources) | 0.026 s | scratch measure, `:SINGle` + `*OPC?` + `:WAV:PRE?` |
| capture 4 × 250,000 over the loopback socket (2.0 MB) | 0.454 s wall; peak RSS 45.6 MB (from 28.7 MB at start) | `ScopeClient.capture`, `getrusage` |
| acquire 4 × 1,000,000 | 0.159 s | same |
| capture 4 × 1,000,000 (8.0 MB) | 1.001 s wall; peak RSS 87.7 MB | same |

Memory grows about 8 MB per million samples held (numpy int64 working arrays + the bytes); the profile's maximum — four channels at the
5 Mpts four-channel depth — would hold ~20 M samples (~160 MB), inside the 256 MB limit but the knob to watch; the default depth is 10,000.

Reproducibility: the emulator's samples are a pure function of the source specs, the settings and the acquisition number (noise is seeded by
both), so a capture's `source_ref` + the stored block reproduce byte-for-byte; the selftests check the block's sha256 against the emulator's own.

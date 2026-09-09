# Collab (`collab`)

Collaboration sessions (mtg-2, LIVEKIT_COLLABORATION_PLAN v2): one session object, many client surfaces (browser meeting, sim-side voice, VR). CollaborationSession + MeetingRecord rows; KC-verified callers mint short-lived LiveKit JWTs (pure-stdlib HS256 — no SDK); capability/join-info with the *_remote refusal ladder. THE LINE: nothing arriving over LiveKit mutates Polari state. Second module born manifest-first on dyn-1.

**Kind:** polari-app · **agent tier:** member · **requires:** nothing

## Objects

`AvatarDefinition`, `CollabAPI`, `CollaborationSession`, `MeetingRecord`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `avatar_basis.py`, `collab_basis.py`
- **api** — `collab_api.py`
- **remote** — `livekit_remote.py`
- **custom** — `custom/realtime_schemas.py`
- **selftests** — `collab_selftest.py`

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Selftest

```
pol modules selftest collab        # in the running backend
PYTHONPATH=.:modules python3 -m collab.collab_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform collab`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

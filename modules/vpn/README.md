# Vpn (`vpn`)

Isle VPN (vpn-1): the isle-vpn app family (Isle Link = WireGuard-based, Isle Bridge = OpenVPN-based, ten kinds, Blind / Sees-traffic on every row) — Polari MIRRORS each isle's VPN app state (networks, peers with public keys only, access rules, federation links, .vpn exposures; POST /api/islemesh/ingest/vpn) and PROPOSES changes an operator applies on the isle (VpnProposal inbox; D9 authority is isle-side). Engine renders Link confs / nftables text; Bridge refuses until step-ca. Feeds /display/vpn and the .vpn column of /display/isle-mesh.

**Kind:** polari-app · **agent tier:** member · **requires:** islemesh

**Catalog kinds this module adds:** isle-vpn

## Objects

`AppVpnExposure`, `VpnAPI`, `VpnAccessRule`, `VpnFederationLink`, `VpnNetwork`, `VpnPeer`, `VpnProposal`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/vpn/AppVpnExposure.py`, `objects/vpn/VpnAccessRule.py`, `objects/vpn/VpnFederationLink.py`, `objects/vpn/VpnNetwork.py`, `objects/vpn/VpnPeer.py`, `objects/vpn/VpnProposal.py`, `objects/vpn/_shared.py`
- **basis** — `vpn_basis.py`
- **api** — `vpn_api.py`
- **seed** — `vpn_seed.py`
- **page** — `vpn_page.py`
- **catalog** — `vpn_catalog.py`
- **custom** — `custom/vpn_constants.py`, `custom/vpn_demo.py`, `custom/vpn_engine.py`, `custom/vpn_proposals.py`, `custom/vpn_trust.py`
- **selftests** — `vpn_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `vpn.vpn_page:SEED_VPN_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest vpn        # in the running backend
PYTHONPATH=.:modules python3 -m vpn.vpn_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform vpn`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

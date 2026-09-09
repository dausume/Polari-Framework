# Sifet (`sifet`)

Silicon MOSFETs (planar / FinFET) on thermal and SOL-GEL dielectrics sharing the cntfet VS device contract (states, regimes, scoring, validity, cross-technology ranking), complementary pairs, and silicon refinement routes (MG -> UMG -> SoG -> EG; PV open, EG novel).

**Kind:** library · **agent tier:** member · **requires:** cntfet

## Objects

`RefinementRoute`, `RefinementStep`, `SiliconDopingProfile`, `SiliconFETShape`, `SiliconGrade`, `SiliconMOSFET`, `SiliconProcessNode`, `SolGelDielectric`, `SolGelProcess`

## Layout (the Standardized Polari App, postfix names)

- **basis** — `si_basis.py`, `si_ladder_basis.py`, `si_refinement_basis.py`
- **seed** — `sifet_data_seed.py`
- **page** — `si_page.py`
- **custom** — `custom/si_device.py`, `custom/si_fields.py`, `custom/si_model.py`, `custom/si_montecarlo.py`, `custom/si_scene.py`, `custom/si_transport.py`
- **selftests** — `ladder_selftest.py`, `refinement_selftest.py`, `si_fields_selftest.py`, `si_scene_selftest.py`, `si_sequential_selftest.py`, `si_transport_selftest.py`, `sifet_pages_selftest.py`, `sifet_selftest.py`
- **initialData/** — module-initial-data/1 rows (non-regenerable data only)

`polari-app.json` is the manifest the core reads; `custom/` holds code that fits no concept file.

## Pages

- `sifet.si_page:SEED_SI_PAGE_DISPLAYS`
- `sifet.si_page:SEED_SI_SCORE_PAGES`

## Selftest

```
pol modules selftest sifet        # in the running backend
PYTHONPATH=.:modules python3 -m sifet.ladder_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform sifet`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

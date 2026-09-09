# Climate (`climate`)

Climate Change & Atmosphere: CO2 series as objects (ice-core + instrumental spans), velocity/acceleration fits, graded health thresholds, the coupled indoor/outdoor crossing projection, XPORT ingest for NHANES biomarkers, and the human-history record.

**Kind:** polari-app · **agent tier:** member · **requires:** aquaponics, dmvdata

## Objects

`AmbientSettingProfile`, `AtmosphereSeriesBinding`, `AtmosphericObservation`, `AtmosphericSeriesDefinition`, `AtmosphericTrendFit`, `BiomarkerCycleObservation`, `CO2HealthThreshold`, `CarbonSinkSeries`, `ClimateAPI`, `ExposureProjection`, `HealthSymptomDefinition`, `HumanEraDefinition`, `IndoorSpaceProfile`, `ObservedLevelReference`, `PopulationBiomarkerSeries`, `SeriesCompressionRecord`, `SourceCoverageSpan`, `SymptomOnsetClaim`

## Layout (the Standardized Polari App — see modules/README.md for what each entry means)

- **objects** — `objects/climate/AmbientSettingProfile.py`, `objects/climate/AtmosphericObservation.py`, `objects/climate/AtmosphericSeriesDefinition.py`, `objects/climate/AtmosphericTrendFit.py`, `objects/climate/BiomarkerCycleObservation.py`, `objects/climate/CO2HealthThreshold.py`, `objects/climate/CarbonSinkSeries.py`, `objects/climate/ExposureProjection.py`, `objects/climate/HealthSymptomDefinition.py`, `objects/climate/HumanEraDefinition.py`, `objects/climate/IndoorSpaceProfile.py`, `objects/climate/ObservedLevelReference.py`, … (8 more)
- **basis** — `climate_basis.py`, `climate_compress_basis.py`, `sim_binding_basis.py`
- **api** — `climate_api.py`
- **seed** — `biomarker_ingest_seed.py`, `carbon_sinks_seed.py`, `climate_app_seed.py`, `climate_citations_seed.py`, `climate_history_seed.py`, `climate_series_seed.py`, `climate_sources_seed.py`, `climate_views_seed.py`, `co2_indoor_seed.py`, `co2_settings_seed.py`, `co2_symptoms_seed.py`, `co2_thresholds_seed.py`
- **page** — `climate_page.py`
- **custom** — `custom/biomarker_link.py`, `custom/climate_claims.py`, `custom/climate_export.py`, `custom/co2_biochemistry.py`, `custom/co2_combustion.py`, `custom/co2_crossing.py`, `custom/co2_disorders.py`, `custom/co2_physiology.py`, `custom/co2_scenarios.py`, `custom/co2_trend.py`, `custom/series_ingest.py`, `custom/series_parsers.py`, … (2 more)
- **selftests** — `climate_selftest.py`, `compress_selftest.py`

`polari-app.json` is the manifest the core reads; `objects/` holds one class per file; `custom/` holds code that fits no concept file.

## Pages

- `climate.climate_page:SEED_CLIMATE_PAGE_DISPLAYS`

## Selftest

```
pol modules selftest climate        # in the running backend
PYTHONPATH=.:modules python3 -m climate.climate_selftest   # on the host, from polari-framework/
```

Conformance: `pol modules conform climate`

<!-- generated from polari-app.json by `pol modules manifests readme`; edit freely — the generator never overwrites a README without this marker -->

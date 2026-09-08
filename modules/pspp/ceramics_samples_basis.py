"""
@module pspp.ceramics_samples_basis

mtt-2 ceramics: concrete CERAMIC SAMPLES for real use cases, arranged
as a "gradual escalating temperature resistance" ladder — from
locally-fired earthenware up to steelmaking-grade refractories — with
TWO parallel top-of-ladder tracks:

  LOCAL track (pure locally-producible): clay bodies -> fireclay
    firebrick -> mullite/alumina -> dolomitic BASIC refractory. Every
    feedstock is household or common-industrial.
  OLIVINE track (non-local but optimized, CARBON-NEGATIVE): forsterite
    (from mined olivine) — a basic refractory whose olivine feedstock
    carbonates CO2 (Mg2SiO4 + 2CO2 -> 2MgCO3 + SiO2), the critical
    carbon-negative pathway. Flagged mined-nonlocal, honestly.

Each sample records its feedstocks + accessibility tier, an
APPROXIMATE-literature service/softening temperature (claim_status
says so; a datasheet refines it — no false precision), thermal-shock
behaviour (the "gradual escalating" tolerance), refractory class
(acidic/basic/neutral — basic resists steelmaking slags), a carbon
profile, and the use cases it serves.

Honesty: temperatures are textbook-approximate CITED claims, not
measured for a specific body; carbon-negative sequestration NUMBERS
refuse until the olivine-carbonation dataset is digitized (only the
stoichiometry is exact).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - pspp.ceramics_ladder_basis (linings the escalation rungs require)
  - pspp.pspp_api (/api/pspp/ceramics/samples)
  - pspp.ceramics_samples_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/ceramics_samples/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from pspp.solgel_sourcing_basis import ACCESSIBILITY_TIERS, _tier_rank
import json

from pspp.objects.ceramics_samples._shared import CARBON_PROFILES, REFRACTORY_CLASSES, SEED_CERAMICS_DATASETS, SEED_CERAMIC_SAMPLES, TEMP_CLAIM, THERMAL_SHOCK, _CER_PROV, _fs, _row, sample_dict, samples_meeting_temp, temperature_ladder, validate_samples  # noqa: F401
from pspp.objects.ceramics_samples.CeramicSample import CeramicSample  # noqa: F401

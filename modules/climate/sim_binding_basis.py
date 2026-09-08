"""
@module climate.sim_binding_basis

co2-9 — THE PROOF THAT THESE ARE OBJECTS, NOT A PAGE.

`AtmosphereDefinition.outside_co2_ppm` (aquaponics) is a seeded
constant: 420.0. A greenhouse simulation running on it is running
on a number somebody typed. This module points it at the INGESTED
Mauna Loa record instead, so the ambient CO2 in a plant-growth
simulation is the CO2 the world actually had.

DIRECTION MATTERS. The binding lives here and PUSHES, rather than
aquaponics pulling from climate, for three reasons:

1. `climate` already requires `aquaponics` (it reuses the
   steady-state gas balance). A pull would make that circular.
2. `AtmosphereDefinition` needs no new field, so the seed
   field-addition gotcha never fires.
3. `pol modules drop climate` leaves aquaponics working exactly
   as it did before - the atmosphere rows keep whatever value was
   last written, and the binding rows that explain it go away
   with the module that made them.

WHAT A BINDING PROMISES, AND WHAT IT DOES NOT. It writes a
MEASURED value in place of a guessed one and records what it
replaced. It does NOT claim the greenhouse is in Hawaii: Mauna
Loa is a clean-air baseline, and a real greenhouse sits in a
local airshed that is usually higher. The binding says so on the
row rather than letting the precision of the number imply a
precision of place.

The seeded constant stays the FALLBACK. If the series has not
been ingested, the binding refuses and the simulation runs on the
constant it always used - never on a half-applied binding.

@consumers climate.climate_api, climate.climate_selftest,
polariServer
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/sim_binding/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import datetime
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import rows
from composition.custom.seed_upsert import upsert_seed_pairs

from climate.objects.sim_binding._shared import BINDING_MODES, PROV, SEED_ATMOSPHERE_BINDINGS, _named, _now, apply_all, apply_binding, binding_report, resolve_value  # noqa: F401
from climate.objects.sim_binding.AtmosphereSeriesBinding import AtmosphereSeriesBinding  # noqa: F401

from composition.custom.seed_upsert import upsert_seed_pairs

def seed_atmosphere_bindings(manager):
    return upsert_seed_pairs(manager, [
        ('AtmosphereSeriesBinding', AtmosphereSeriesBinding,
         SEED_ATMOSPHERE_BINDINGS),
    ], tag='ClimateBindingSeed')

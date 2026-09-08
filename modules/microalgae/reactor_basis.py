"""
@cross-cutting
@module microalgae.reactor_basis
@tags @xc:bindings

Microalgae photobioreactor models (algae-1) — the DE-CARBONIZATION
route for hydroponic + saltwater-food-forest systems. Own module + own
data, framework-core only (a lazy read of a coupled tank's balance is
the only cross-module touch, in reactor_analysis).

The core purpose (Dustin): hook a reactor to a parent system (aquaponics
pot loop / tank food forest / hydroponic reservoir) to FIX CO2 — but
SUSTAINABLY, so the reactor's nutrient draw never exceeds what the
parent can spare (else the parent depletes or the algae crash and the
whole system collapses). The nutrient_draw_cap knob is the model of the
spec's biochar passthrough limiter.

Two treeObjects (auto-CRUDE + persisted — object-coherence):

  AlgaeStrain             one microalga: growth rate, C/N/P
                          stoichiometry, carrying density, product, and
                          (if edible) its harvest nutrients.
  AlgaeReactorDefinition  one reactor: strain, volume, light, CO2
                          supply, the COUPLED parent system, and the
                          REGULATION knobs (draw cap, harvest cadence,
                          operating density) that keep it stable.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - microalgae.custom.reactor_analysis (growth, sustainability, decarbonization)
@see /SALTWATER_FOOD_FOREST_SPEC.md (biochar passthrough), tanks/
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/reactor/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from microalgae.objects.reactor._shared import ALGAE_PRODUCTS, CO2_SUPPLY_MODES, COUPLED_KINDS, WATER_TYPES  # noqa: F401
from microalgae.objects.reactor.AlgaeStrain import AlgaeStrain  # noqa: F401
from microalgae.objects.reactor.AlgaeReactorDefinition import AlgaeReactorDefinition  # noqa: F401

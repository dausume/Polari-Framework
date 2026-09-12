"""
@module motors.clock_views_basis

view-1 (MOTOR_GOALS_PLAN goal-5 backend): SPECIALIZED VIEWS AS DATA.

Dustin 2026-07-31: views for clocks using the general M0 approach —
switch between scales, modulate goals and constraints, and SPLIT the
machine apart by discipline: a mechanical-engineering view (physical
failure conditions, stresses), an electrical-engineering view with
electrical and magnetic SEPARABLE, materials provenance/sourcing,
mass, movement simulation, cost from chosen provenance with
dependency tracing — at multiple scales, plus component-focused
views.

THE SHAPE: a view is a ClockViewDefinition ROW — discipline +
ordered sections, each section naming a SOURCE (an existing engine
entry point) and its args. The page renders rows; adding a view is
an insert, not a component. Sections that cannot answer REFUSE
inside the payload with the reason and the knob — a discipline view
never silently drops a panel.

Every source is an engine that already exists (stress, fatigue,
contact, winding, inductance+validity, accountability chain, bill,
clock sim, lifecycle cost, goal engine, composition splice). The one
that does not — the mechanical TENSOR field over a part — ships as a
NAMED GAP section, stating exactly what would wire it (fem_engine
elasticity export), never silently absent.

@consumers motors.motor_api, motors.motors_selftest,
polariServer seed passes (seed_clock_views — upsert path)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/clock_views/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import resolve_named, rows
from moduleService.seed_upsert import upsert_seed_pairs
from motors.clock_scene_basis import scene_json_for_view  # noqa: E402

from motors.objects.clock_views._shared import DISCIPLINES, PROV, SECTION_RENDERERS, SECTION_SOURCES, SEED_CLOCK_VIEWS, _derived_links, _failure_conditions, _j, _src_design, _src_part, _stress_tensor_gap, _view_seed, component_view, view_payload  # noqa: F401
from motors.objects.clock_views.ClockViewDefinition import ClockViewDefinition  # noqa: F401

from moduleService.seed_upsert import upsert_seed_pairs

def seed_clock_views(manager):
    return upsert_seed_pairs(manager, [
        ('ClockViewDefinition', ClockViewDefinition,
         SEED_CLOCK_VIEWS),
    ], tag='ClockViewsSeed')

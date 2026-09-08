"""
@module motors.clock_scene_basis

viz-1 (Dustin 2026-07-31): "specialized sim space displays on all of
the varying views ... changing through different 3D visualizations
and being able to overlap them as well." The clock views must LEAD
with 3D, not JSON — so the visualizations are LAYERS on one scene,
switchable per discipline and stackable in any combination.

THE SHAPE: a layer is a ClockSceneLayerDefinition ROW — a kind the
renderer already knows how to draw, the engine that feeds it, and
the mapping as params. Adding a visualization is an insert, not a
component. Kinds map 1:1 onto proven renderer capabilities
(sim-space three-renderer):

  part-coloring — per-body colorOverride computed from an engine
                  (mass fractions, stress SF thresholds, material
                  palette); carries a legend
  vector-field  — SnapshotVector arrows (rides the mag-fv field
                  view payloads unchanged)
  replay        — the solver-history animation; the layer carries
                  the GEOMETRY CONFIG (rotor bodies, axis, coil
                  styles) that previously lived hard-coded in the
                  Angular motor page
  markers       — extra builtin-shape bodies (the field-shells
                  idiom): interface joints, colored by whether
                  their failure modes are modelled

A layer that cannot answer REFUSES inside the payload with the
reason and the knob — never dropped, never a blank canvas. The
part→body map is DATA on the coloring layers (it also existed as a
buggy hard-coded table in clock-motor.component; this is the one
copy now).

@consumers motors.motor_api (/api/motors/clock-scene/{view}),
motors.motors_selftest, polariServer seed pass (upsert path, with
seed_clock_views)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/clock_scene/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

import json
from objectTreeDecorators import treeObject, treeObjectInit
from composition.custom.data_refs import resolve_named, rows
from composition.custom.seed_upsert import upsert_seed_pairs

from motors.objects.clock_scene._shared import ALL_LAYERS, GEAR_TRAIN_SCENE, LAYER_KINDS, PALETTE, PROV, SEED_CLOCK_SCENE_LAYERS, V2_BASE, V2_PART_BODIES, VIEW_SCENES, _j, _markers, _mass_coloring, _material_coloring, _ramp, _shape_swap, _stress_coloring, _vector_field, clock_scene_payload, layer_payload, mass_bodies, scene_json_for_view  # noqa: F401
from motors.objects.clock_scene.ClockSceneLayerDefinition import ClockSceneLayerDefinition  # noqa: F401

from composition.custom.seed_upsert import upsert_seed_pairs

def seed_clock_scene(manager):
    """Layer rows via the upsert path (converge live rows)."""
    return upsert_seed_pairs(
        manager,
        [('ClockSceneLayerDefinition', ClockSceneLayerDefinition,
          SEED_CLOCK_SCENE_LAYERS)],
        tag='ClockSceneSeed')

"""
@cross-cutting
@module simSpace3D.material_phase_appearance
@tags @xc:render-3d, @xc:bindings

PER-MATERIAL-PHASE appearance: a named, reusable row tying a SUBSTANCE
(the material picker's choice key) to the render material each PHASE of
that substance should wear — e.g. paraffin wax: solid → 'wax-solid'
(off-white, noisy), liquid → 'wax-liquid' (translucent amber).

Object coherence: this row is the object-level home of "what does this
material look like per phase". Scene bindings consume it as the inline
`{fromField, map, default}` styleRef primitive (compilers stay
independent of this class); the seed helper `binding_style_map()`
composes the inline map FROM a row so the two can never drift. The
selection space (Phase C) and module export (Phase D) reference these
rows by name.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - simulations.material_space_scene_seed (binding style maps)
  - Phase C sim-space-selector (appearanceRef per selectable material)
@see /OVERLAP_MAP.md
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit


class MaterialPhaseAppearance(treeObject):
    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # The substance's identity — matches the IC picker choice key
        # ('paraffin-wax', 'water-ice', 'lead').
        substance_ref: str = '',
        # The state FIELD whose value selects the phase (configurable to
        # data — today the binary phase_solid; schema stays open for
        # richer phase fields later).
        phase_field: str = 'phase_solid',
        # phase value (stringified) → Material3DDefinition name, e.g.
        # {"1": "wax-solid", "0": "wax-liquid"}.
        appearance_map_json: str = '{}',
        # Fallback material when the phase value maps to nothing.
        default_material_ref: str = 'matte-gray',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.substance_ref = substance_ref
        self.phase_field = phase_field
        self.appearance_map_json = appearance_map_json
        self.default_material_ref = default_material_ref


def binding_style_map(row_dict):
    """Compose a scene binding's inline styleRef spec FROM an appearance
    row dict (seed-time helper — keeps binding maps and appearance rows
    from drifting): {fromField, map, default}."""
    try:
        appearance_map = json.loads(
            row_dict.get('appearance_map_json') or '{}')
    except (TypeError, ValueError):
        appearance_map = {}
    return {
        'fromField': row_dict.get('phase_field') or 'phase_solid',
        'map': appearance_map,
        'default': row_dict.get('default_material_ref') or 'matte-gray',
    }

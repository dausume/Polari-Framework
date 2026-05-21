"""
@cross-cutting
@module simSpace.sim_space_binding_definition
@tags @xc:render-shared, @xc:bindings

Per-class SimSpace binding — how to render instances of a class in a
SimSpace of a given dimensionality. One row per (class_name, dimensionality)
pair, so a class can be bound 2D-only, 3D-only, or both independently.

The binding's specifics live in `binding_json` as a JSON blob whose
shape matches `SimSpaceBinding` in /models/sim-space/sim-space-types.ts.
Keeping the details in JSON avoids schema churn on every binding-model
tweak and matches how every other Polari Definition class stores its
config.

@consumers
  - polariServer.defClassList (auto-CRUDE)
  - simSpace/sim_space_api.py (snapshot compiler walks bound classes)
  - frontend SimSpaceBindingService + binding tab
@impact-on-edit
  Don't add columns lightly — every new column hits the DB schema.
  Prefer extending binding_json.
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimSpaceBindingDefinition(treeObject):
    @treeObjectInit
    def __init__(
        self,
        # Unique identity: f"{class_name}-{dimensionality}".
        # E.g. "EquationDefinition-2d", "MyClass-3d".
        name: str = '',
        class_name: str = '',
        dimensionality: str = '2d',
        enabled: bool = False,
        # JSON-encoded binding payload matching SimSpaceBinding in the
        # frontend. Includes position binding (fields or vec3 ref),
        # optional rotation/scale, shape+style ref, filter expression,
        # click action, defaultVisible flag.
        binding_json: str = '{}',
        manager=None,
    ):
        self.name = name
        self.class_name = class_name
        self.dimensionality = dimensionality
        self.enabled = enabled
        self.binding_json = binding_json

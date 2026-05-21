"""
@cross-cutting
@module simSpace.sim_space_definition
@tags @xc:render-shared

Base Definition class for the SimSpace abstraction. Mirrors how
EquationDefinition / DataSetDefinition / GeoJsonDefinition are structured —
a small metadata header + a JSON blob (`definition`) that's dimension-
specific. The dimensionality flag drives the snapshot dispatcher.

Stored in MariaDB via the auto-table-creation flow used by every other
Definition class (registered in polariServer.defClassList).

Why one class, not two: per the SimSpace plan, the 2D and 3D variants
share enough config (name, description, coordinate system, viewport,
bound classes) that a separate Definition per dimensionality would be
duplicate plumbing. The dimensionality field disambiguates; the
`definition` blob holds whatever the dimension needs internally.

@consumers
  - polariServer.defClassList (registration → auto-CRUDE)
  - simSpace/api/sim_space_api.py (snapshot dispatcher)
  - simSpace2D/api/* (per-dimension list endpoints filter on dimensionality)
  - frontend SimSpaceService

@impact-on-edit
  Adding a column changes the DB schema — fresh deploys get the new
  column, existing deploys go through the Definition table migration
  path (initializeVarsFromSignature → makeTypedTableFromAnalysis).
  Test with both a fresh volume AND an existing one.
@see /OVERLAP_MAP.md and /polari-framework/simSpace-IMPACT.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class SimSpaceDefinition(treeObject):
    """A configurable visual space (2D or 3D) where objects can be placed.

    Identity: name (must be unique within a deployment).
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # '2d' | '3d' — drives renderer dispatch on the frontend and
        # snapshot compiler dispatch on the backend.
        dimensionality: str = '2d',
        # 'math' | 'screen' — math is origin-center, Y-up (scientific
        # default). Screen is origin-top-left, Y-down (no-code-style).
        coordinate_system: str = 'math',
        # Multiplier applied to position bindings. Defaults to 1.0
        # ("1 unit = 1 unit"). Useful when a class stores positions in
        # millimeters but the scene is configured in meters.
        unit_scale: float = 1.0,
        # JSON-encoded viewport bounds: {"center": [x,y(,z)], "extent": [x,y(,z)]}.
        # When empty, frontend renderers fall back to a sensible default
        # (math: ±10 each axis; screen: full host element).
        viewport_json: str = '',
        # JSON-encoded array of bound-class overrides:
        # [{"className": ..., "overrideShapeRef": ..., "overrideStyleRef": ...}, ...]
        # Independent of per-class binding config — this is the
        # *scene*-side opt-in; the binding itself lives on the class.
        bound_classes_json: str = '[]',
        # Dimension-specific blob. For 2D: array of freestanding shapes,
        # background config, etc. For 3D: Three.js Object3D.toJSON() output.
        # Opaque to the shared layer.
        definition: str = '{}',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.dimensionality = dimensionality
        self.coordinate_system = coordinate_system
        self.unit_scale = unit_scale
        self.viewport_json = viewport_json
        self.bound_classes_json = bound_classes_json
        self.definition = definition

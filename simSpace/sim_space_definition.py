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
        # JSON-encoded per-axis label override. Shape:
        # {
        #   "x": {"kind": "default" | "text" | "latex", "value": "<str>"},
        #   "y": {...},
        #   "z": {...}
        # }
        # Empty/missing → renders the dimensionality default (X / Y / Z).
        # 'text' renders the value as plain text; 'latex' renders via KaTeX
        # so an axis can carry symbolic notation (e.g. \omega, \theta).
        # Phase-space scenes lean heavily on this — `theta` on X / `omega`
        # on Y is much clearer as "\theta" / "\omega" than literal X / Y.
        axis_labels_json: str = '{}',
        # JSON-encoded camera config (3D scenes). Shape:
        # {"mode": "fixed" | "orbit", "position": [x,y,z],
        #  "target": [x,y,z], "up": [x,y,z],
        #  "projection": "perspective" | "orthographic", "fov": 50}
        # Empty → today's behavior (orbit controls, initial framing from
        # viewport_json). mode='fixed' locks the camera — the config for
        # SELECTION SPACES, where stable framing beats free navigation.
        # NOTE (migration): added 2026-07-06; existing volumes gain the
        # column via the boot schema sync.
        camera_json: str = '',
        # --- XR (xr-1, WEBXR_PLAN.md) -------------------------------
        # Explicit space category — the Q1b vocabulary keying
        # XrTypeDefault rows (e.g. 'hydroponics-layout', 'msim-world').
        # Empty = derive from owning_module (xr_resolution).
        category: str = '',
        # The module that seeded/owns this space (e.g. 'aquaponics') —
        # supplies the DERIVED category default when `category` is
        # unset. Seeds set it going forward; legacy rows resolve past
        # the type level honestly.
        owning_module: str = '',
        # Individual (lowest, always-wins-when-set) rung of the XR
        # cascade: 'unset' | 'none' | 'vr' | 'ar' | 'both' and
        # 'unset' | 'inside' | 'exhibit'.
        xr_mode: str = 'unset',
        xr_framing: str = 'unset',
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
        self.axis_labels_json = axis_labels_json
        self.camera_json = camera_json
        self.category = category
        self.owning_module = owning_module
        self.xr_mode = xr_mode
        self.xr_framing = xr_framing

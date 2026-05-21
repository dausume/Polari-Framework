"""
@cross-cutting
@module simSpace2D.shape_2d_definition
@tags @xc:render-2d, @xc:bindings, @xc:maps

A reusable 2D shape — a named SVG geometry referenceable by SimSpaceBinding.
Plays the role SvgIconDef plays today; long-term consolidation point.

@consumers
  - polariServer.defClassList (registration → auto-CRUDE)
  - SimSpace2D viewer (resolves shapeRef → this row)
  - Per-class Sim Space → 2D binding tab (dropdown source)
  - Maps marker library (post-migration; today still reads SvgIconLibrary)
@impact-on-edit
  Adding a built-in shape that overlaps with an SvgIconDef will create a
  visible duplicate in the UI until SvgIconLibrary is fully absorbed.
  Track in OVERLAP_MAP's Maps consolidation row.
@see /OVERLAP_MAP.md and /polari-framework/simSpace-IMPACT.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class Shape2DDefinition(treeObject):
    """A named 2D shape.

    `source` distinguishes builtins (no params, frontend handles the
    geometry given the shape name) from custom SVGs (the `svg_string`
    field carries the markup). Builtins are bundled with the platform;
    custom SVGs let users define new shapes without backend deploys.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # 'builtin' | 'svg'
        # builtin → frontend recognizes the name (circle, rectangle,
        #   diamond, triangle, star, pin) and renders accordingly.
        # svg → the svg_string field is the raw markup.
        source: str = 'builtin',
        # For builtins, this is the canonical name.
        builtin_name: str = '',
        # For source=='svg'. Empty otherwise.
        svg_string: str = '',
        # Default size hint when no styleRef overrides — used by the
        # binding-tab preview before a style is picked. 24×24 matches
        # SvgIconLibrary's existing defaults.
        default_width: float = 24.0,
        default_height: float = 24.0,
        # 'center' | 'bottom' — where the shape's anchor maps to its
        # placement coordinate. Same semantics as SvgIconLibrary's
        # IconAnchor + GeoJsonConfigData's mapAnchor.
        anchor: str = 'center',
        # 'general' | 'marker' | 'state-machine' | 'custom' — UI grouping.
        category: str = 'general',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.source = source
        self.builtin_name = builtin_name
        self.svg_string = svg_string
        self.default_width = default_width
        self.default_height = default_height
        self.anchor = anchor
        self.category = category

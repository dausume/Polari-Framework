"""
@cross-cutting
@module simSpace2D.style_2d_definition
@tags @xc:render-2d, @xc:bindings, @xc:maps

A reusable 2D style — fill/stroke/opacity bundle referenced by name.
Plays the role SvgIconStyle plays today; long-term consolidation point
the same way Shape2DDefinition consolidates SvgIconDef.

@consumers
  - polariServer.defClassList
  - SimSpace2D viewer (resolves styleRef → this row)
  - Per-class Sim Space → 2D binding tab
  - Maps marker library (post-migration)
@impact-on-edit
  Existing SvgIconStyle names should not collide with seeded styles
  until consolidation is complete (Phase 1 seeds with distinct names).
@see /OVERLAP_MAP.md and /polari-framework/simSpace-IMPACT.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class Style2DDefinition(treeObject):
    """A named 2D style.

    Holds presentation parameters that get applied to a Shape2D when
    rendered. Sized 0..1 for opacity; color values are CSS strings the
    frontend passes straight to SVG fill / stroke attributes.
    """

    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # Pixel size hints. Override Shape2D's default_width/height.
        # Defaults sized for typical viewport scales — too-small values
        # look like dots when a scene is zoomed out.
        width: float = 40.0,
        height: float = 40.0,
        # CSS color strings — anything SVG fill/stroke accepts.
        fill_color: str = '#1976d2',
        stroke_color: str = '#0d47a1',
        stroke_width: float = 1.5,
        opacity: float = 1.0,
        # 'center' | 'bottom' — overrides the shape's anchor when set.
        # Same semantics as SvgIconStyle.anchor.
        anchor: str = 'center',
        # Optional inline label config — when non-empty, the renderer
        # paints a text label next to the rendered shape.
        # Example: {"text": "from-field:name", "offset": [0, -20], "fontSize": 12}
        label_json: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.opacity = opacity
        self.anchor = anchor
        self.label_json = label_json

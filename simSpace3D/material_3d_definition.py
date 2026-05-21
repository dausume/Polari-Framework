"""
@cross-cutting
@module simSpace3D.material_3d_definition
@tags @xc:render-3d, @xc:bindings

A reusable 3D material. Phase 2 covers MeshStandardMaterial parameters
only — emissive PBR, no textures yet. Textures + GLTF materials come
in a later phase via Texture3DDefinition + GLTFLoader integration.

@consumers
  - polariServer.defClassList
  - ThreeSimSpaceRenderer (resolves materialRef → this row)
@impact-on-edit
  Field names must stay aligned with the frontend Material3DDef interface.
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class Material3DDefinition(treeObject):
    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # 'basic' | 'lambert' | 'phong' | 'standard' | 'physical'
        material_type: str = 'standard',
        # CSS color string for the diffuse / albedo.
        color: str = '#1976d2',
        # Emissive color + intensity.
        emissive: str = '#000000',
        emissive_intensity: float = 0.0,
        # PBR knobs (standard / physical materials).
        metalness: float = 0.0,
        roughness: float = 0.5,
        # Transparency.
        opacity: float = 1.0,
        transparent: bool = False,
        # Whether to draw both sides (useful for planes).
        double_sided: bool = False,
        # Flat shading toggles per-face normals.
        flat_shading: bool = False,
        # Wireframe debug mode.
        wireframe: bool = False,
        manager=None,
    ):
        self.name = name
        self.description = description
        self.material_type = material_type
        self.color = color
        self.emissive = emissive
        self.emissive_intensity = emissive_intensity
        self.metalness = metalness
        self.roughness = roughness
        self.opacity = opacity
        self.transparent = transparent
        self.double_sided = double_sided
        self.flat_shading = flat_shading
        self.wireframe = wireframe

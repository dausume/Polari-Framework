"""
@cross-cutting
@module simSpace3D.mesh_3d_definition
@tags @xc:render-3d, @xc:bindings

A reusable 3D mesh — plays the role Shape2DDefinition plays for 2D.
Phase 2 covers builtin primitives only (cube, sphere, cylinder, plane,
cone). glTF uploads + custom Three.js JSON come in a later phase.

@consumers
  - polariServer.defClassList
  - ThreeSimSpaceRenderer (resolves meshRef → this row)
  - Per-class Sim Space → 3D binding tab (Phase 2.5+ dropdown)
@impact-on-edit
  Field names must stay aligned with the frontend Mesh3DDef interface.
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class Mesh3DDefinition(treeObject):
    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # 'builtin' | 'gltf' | 'three-json'  (Phase 2: builtin only)
        source: str = 'builtin',
        # For builtins, one of: cube, sphere, cylinder, plane, cone, torus
        builtin_name: str = '',
        # JSON: builtin-specific args (radius, segments, width, height, ...)
        primitive_params_json: str = '{}',
        # For gltf source — Phase 2.5+ uploads
        s3_bucket: str = '',
        s3_object_key: str = '',
        # For three-json — inline definition blob
        inline_definition: str = '',
        # JSON: {"min": [x,y,z], "max": [x,y,z]} — precomputed AABB
        bounding_box_json: str = '',
        manager=None,
    ):
        self.name = name
        self.description = description
        self.source = source
        self.builtin_name = builtin_name
        self.primitive_params_json = primitive_params_json
        self.s3_bucket = s3_bucket
        self.s3_object_key = s3_object_key
        self.inline_definition = inline_definition
        self.bounding_box_json = bounding_box_json

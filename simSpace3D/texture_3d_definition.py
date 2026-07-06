"""
@cross-cutting
@module simSpace3D.texture_3d_definition
@tags @xc:render-3d, @xc:bindings

A reusable 3D-applicable TEXTURE — the "later phase" the material module
reserved. Physical materials map to textures (surface appearance), not
to meshes (geometry): a Material3DDefinition references a texture via
`map_texture_ref` and the frontend texture builders turn this row into a
THREE.Texture.

Procedural-first (checker / stripes / gradient / noise generated on a
canvas — self-contained, exports cleanly in module bundles); `source:
'image'` + the S3 fields are the knob for file-store-backed image
textures (MinIO), wired in a follow-up — same placeholder convention
Mesh3DDefinition uses for GLTF.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - frontend texture-3d-library.service + three-texture-builders
  - MaterialPhaseAppearance (per-phase appearance rows reference
    materials, which reference textures)
@impact-on-edit
  Field names must stay aligned with the frontend Texture3DDef interface.
@see /OVERLAP_MAP.md
"""

from objectTreeDecorators import treeObject, treeObjectInit


class Texture3DDefinition(treeObject):
    @treeObjectInit
    def __init__(
        self,
        name: str = '',
        description: str = '',
        # 'procedural' (canvas-generated) | 'image' (file store, knob —
        # wired in a follow-up).
        source: str = 'procedural',
        # Procedural generator kind: 'checker' | 'stripes' | 'gradient'
        # | 'noise'.
        procedural_kind: str = 'noise',
        # Generator parameters (colors, cell size, octaves, seed …) —
        # opaque JSON interpreted by the frontend builder per kind.
        procedural_params_json: str = '{}',
        # Image source placeholders (MinIO object) — the follow-up knob.
        s3_bucket: str = '',
        s3_object_key: str = '',
        # UV wrapping: 'repeat' | 'clamp' | 'mirror'.
        wrap_s: str = 'repeat',
        wrap_t: str = 'repeat',
        # UV transform.
        repeat_u: float = 1.0,
        repeat_v: float = 1.0,
        offset_u: float = 0.0,
        offset_v: float = 0.0,
        rotation: float = 0.0,
        manager=None,
    ):
        self.name = name
        self.description = description
        self.source = source
        self.procedural_kind = procedural_kind
        self.procedural_params_json = procedural_params_json
        self.s3_bucket = s3_bucket
        self.s3_object_key = s3_object_key
        self.wrap_s = wrap_s
        self.wrap_t = wrap_t
        self.repeat_u = repeat_u
        self.repeat_v = repeat_v
        self.offset_u = offset_u
        self.offset_v = offset_v
        self.rotation = rotation

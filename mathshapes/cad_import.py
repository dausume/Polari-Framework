"""
@cross-cutting
@module mathshapes.cad_import
@tags @xc:bindings, @xc:render-3d

Orchestrates CAD import/export across three seams: the cad-engines
worker (mathshapes.cad_remote), MinIO object storage (mathshapes.
cad_minio), and the object tree (rows created via the same
`cls(**attrs, manager=manager)` idiom the seeder uses).

  capability(manager)          worker + MinIO readiness (honest).
  import_cad(manager, ...)     worker imports the file -> stores the
                               original in MinIO -> creates a
                               Mesh3DDefinition (three-json, renders),
                               a MathShapeDefinition(family='imported-
                               mesh'), and an ImportedCadObject row.
  export_shape(manager, ...)   sample the shape's surface (shape-1
                               sample_surface, or the cached imported
                               mesh) -> worker exports to the requested
                               format (glTF/three-json/STL/STEP/FCStd)
                               -> stores the artifact in MinIO -> returns
                               the object key + a download URL.

Row creation is injectable (the `factory` arg) so selftests can observe
it without the live treeObject machinery.
"""

import base64
import json

from mathshapes import cad_minio, cad_remote

_THREEJS_EXPORT = 'three-json'


# --------------------------------------------------------------------------
# row helpers
# --------------------------------------------------------------------------
def _rows(manager, class_name):
    table = (getattr(manager, 'objectTables', None) or {}).get(
        class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)


def _named(manager, class_name, name):
    for row in _rows(manager, class_name):
        if getattr(row, 'name', '') == name:
            return row
    return None


def _default_factory(manager, class_name, attrs):
    """Instantiate a real treeObject (auto-registers + persists)."""
    if class_name == 'MathShapeDefinition':
        from mathshapes.shape_basis import MathShapeDefinition as cls
    elif class_name == 'Mesh3DDefinition':
        from simSpace3D.mesh_3d_definition import Mesh3DDefinition as cls
    elif class_name == 'ImportedCadObject':
        from mathshapes.cad_basis import ImportedCadObject as cls
    else:
        raise ValueError(f'unknown class {class_name}')
    return cls(**attrs, manager=manager)


def _three_json_inline(points, triangles):
    """Same three.js BufferGeometry JSON the worker emits — so an
    imported mesh renders straight from its Mesh3DDefinition."""
    flat_pos = [c for p in points for c in p]
    flat_idx = [i for f in (triangles or []) for i in f]
    data = {'attributes': {'position': {
        'itemSize': 3, 'type': 'Float32Array',
        'array': flat_pos, 'normalized': False}}}
    if flat_idx:
        data['index'] = {'type': 'Uint32Array', 'array': flat_idx}
    return json.dumps({'metadata': {'version': 4.5, 'type': 'BufferGeometry',
                                    'generator': 'mathshapes.cad_import'},
                       'type': 'BufferGeometry', 'data': data})


# --------------------------------------------------------------------------
# capability
# --------------------------------------------------------------------------
def capability(manager, remote=cad_remote):
    worker = remote.remote_capability()
    minio = cad_minio.store_status(manager)
    return {
        'ok': bool(worker) and minio.get('ok', False),
        'worker': worker or {'ok': False,
                             'error': 'cad-engines worker not reachable',
                             'suggestion': remote.unavailable_suggestion(
                                 'no CAD_ENGINES_URL / provider')},
        'minio': minio,
        'note': 'import/export needs BOTH a reachable cad-engines worker '
                'and a connected MinIO object store.',
    }


# --------------------------------------------------------------------------
# import
# --------------------------------------------------------------------------
def import_cad(manager, filename, data, name=None, display_name='',
               provenance_id='shape-3', factory=None, remote=cad_remote):
    """Import a CAD file end-to-end. `data` is raw bytes."""
    factory = factory or _default_factory
    fmt = (filename or '').lower().rsplit('.', 1)[-1]
    base = name or (filename or 'imported').rsplit('.', 1)[0]
    base = base.replace(' ', '-').replace('_', '-').lower()

    worker_res = remote.remote_post('/cad/import', {
        'filename': filename, 'format': fmt,
        'contentBase64': base64.b64encode(data).decode()})
    if not worker_res.get('ok'):
        return worker_res  # honest refusal carrying the suggestion

    points = worker_res.get('meshPoints', [])
    triangles = worker_res.get('triangles', [])
    bbox = worker_res.get('bbox', [])
    centroid = worker_res.get('centroid', [])
    params = worker_res.get('parametricParams', {}) or {}
    volume = float(worker_res.get('volume', 0.0))

    # 1. persist the ORIGINAL bytes to MinIO.
    minio_key = f'imported/{base}.{fmt}'
    put = cad_minio.put_bytes(manager, cad_minio.IMPORT_BUCKET, minio_key,
                              data, content_type='application/octet-stream')
    if not put.get('ok'):
        return {'ok': False, 'stage': 'minio-store', **put}
    bbox_min = [bbox[i][0] for i in range(3)] if len(bbox) == 3 else [0, 0, 0]
    bbox_max = [bbox[i][1] for i in range(3)] if len(bbox) == 3 else [0, 0, 0]

    # 2. render mesh (three-json, points to the stored original too).
    mesh_name = f'{base}-mesh'
    factory(manager, 'Mesh3DDefinition', {
        'name': mesh_name,
        'description': f'Imported from {filename} via cad-engines',
        'source': _THREEJS_EXPORT,
        'inline_definition': _three_json_inline(points, triangles),
        's3_bucket': cad_minio.IMPORT_BUCKET, 's3_object_key': minio_key,
        'bounding_box_json': json.dumps({'min': bbox_min, 'max': bbox_max})})

    # 3. math shape (family=imported-mesh; cache mesh for re-export).
    shape_name = f'{base}-shape'
    factory(manager, 'MathShapeDefinition', {
        'name': shape_name, 'display_name': display_name or base,
        'family': 'imported-mesh',
        'parameters_json': json.dumps({'meshPoints': points,
                                       'triangles': triangles,
                                       'parametricParams': params}),
        'bounds_json': json.dumps([[bbox_min[i], bbox_max[i]]
                                   for i in range(3)]),
        'notes': f'imported {filename} ({worker_res.get("importer", "")})',
        'provenance_id': provenance_id})

    # 4. the import record.
    cad_name = f'{base}-import'
    factory(manager, 'ImportedCadObject', {
        'name': cad_name, 'display_name': display_name or base,
        'source_filename': filename, 'source_format': fmt,
        'minio_key': f'{cad_minio.IMPORT_BUCKET}/{minio_key}',
        'volume_cm3': volume,
        'bbox_json': json.dumps(bbox), 'centroid_json': json.dumps(centroid),
        'parametric_params_json': json.dumps(params),
        'mesh3d_name': mesh_name, 'shape_name': shape_name,
        'importer': worker_res.get('importer', ''),
        'provenance_id': provenance_id})

    return {'ok': True, 'shape': shape_name, 'mesh3d': mesh_name,
            'importRecord': cad_name, 'minioKey': put['objectPath'],
            'volume': volume,
            'boundingBox': [[bbox_min[i], bbox_max[i]] for i in range(3)],
            'parametricParams': params, 'vertexCount': len(points),
            'importer': worker_res.get('importer', ''),
            'note': 'stored original in MinIO; created render mesh + math '
                    'shape + import record.'}


# --------------------------------------------------------------------------
# export
# --------------------------------------------------------------------------
def _shape_mesh(manager, shape):
    """(points, triangles) for a shape: cached for imported meshes,
    freshly sampled (shape-1) for math shapes."""
    if getattr(shape, 'family', '') == 'imported-mesh':
        try:
            cached = json.loads(getattr(shape, 'parameters_json', '{}'))
        except (TypeError, ValueError):
            cached = {}
        return cached.get('meshPoints', []), cached.get('triangles', [])
    from mathshapes.shape_analysis import sample_surface
    res = sample_surface(manager, getattr(shape, 'name', ''))
    if not res.get('ok'):
        return [], []
    return res.get('points', []), res.get('triangles', [])


def export_shape(manager, shape_name, fmt, factory=None, remote=cad_remote):
    """Export a shape to `fmt` (glb/gltf/three-json/stl/step/fcstd) and
    store the artifact in MinIO. Returns the key + a download URL."""
    shape = _named(manager, 'MathShapeDefinition', shape_name)
    if shape is None:
        return {'ok': False,
                'error': f"no MathShapeDefinition named '{shape_name}'"}
    points, triangles = _shape_mesh(manager, shape)
    if not points:
        return {'ok': False,
                'error': f"shape '{shape_name}' produced no surface mesh to "
                         'export'}

    worker_res = remote.remote_post('/cad/export', {
        'format': fmt, 'meshPoints': points, 'triangles': triangles})
    if not worker_res.get('ok'):
        return worker_res

    try:
        artifact = base64.b64decode(worker_res.get('contentBase64', ''))
    except Exception as e:
        return {'ok': False, 'error': f'worker returned bad payload: {e}'}

    ext = worker_res.get('format', fmt).replace('three-json', 'three.json')
    key = f'exports/{shape_name}.{ext}'
    put = cad_minio.put_bytes(
        manager, cad_minio.EXPORT_BUCKET, key, artifact,
        content_type=worker_res.get('contentType', 'application/octet-stream'))
    if not put.get('ok'):
        return {'ok': False, 'stage': 'minio-store', **put}
    url = cad_minio.presigned_get(manager, cad_minio.EXPORT_BUCKET, key)
    return {'ok': True, 'shape': shape_name, 'format': fmt,
            'minioKey': put['objectPath'], 'bytes': len(artifact),
            'downloadUrl': url.get('url') if url.get('ok') else None,
            'urlNote': None if url.get('ok') else url.get('error'),
            'note': f'exported {shape_name} as {fmt}; stored in MinIO '
                    f'{cad_minio.EXPORT_BUCKET}.'}

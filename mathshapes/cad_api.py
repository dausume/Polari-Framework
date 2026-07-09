"""
@cross-cutting
@module mathshapes.cad_api
@tags @xc:bindings

HTTP surface for CAD import/export (shape-3):

  GET  /api/shapes/cad-capability       worker + MinIO readiness (honest).
  POST /api/shapes/import               upload a CAD file -> shape + mesh +
                                        import record. JSON body
                                        {filename, contentBase64, name?}
                                        or raw bytes with ?filename=.
  POST /api/shapes/{name}/export        {format} -> MinIO key + URL.
  GET  /api/shapes/imports              the ImportedCadObject catalogue.

@consumers
  - mathshapes frontend / SimSpace3D rendering
@see /MATH_SHAPES_PLAN.md (PHASE shape-3)
"""

import base64

from objectTreeDecorators import treeObject, treeObjectInit
from mathshapes import cad_import


class CadImportAPI(treeObject):
    """CAD import/export endpoints."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/shapes/import'
        if polServer is not None:
            polServer.falconServer.add_route(
                '/api/shapes/cad-capability', self, suffix='capability')
            polServer.falconServer.add_route(
                '/api/shapes/import', self, suffix='import')
            polServer.falconServer.add_route(
                '/api/shapes/{name}/export', self, suffix='export')
            polServer.falconServer.add_route(
                '/api/shapes/imports', self, suffix='imports')

    def on_get_capability(self, request, response):
        response.media = cad_import.capability(self.manager)

    def on_post_import(self, request, response):
        ct = (request.content_type or '')
        filename = request.params.get('filename', '')
        name = request.params.get('name')
        data = None
        if 'application/json' in ct:
            body = request.media or {}
            filename = body.get('filename', filename)
            name = body.get('name', name)
            try:
                data = base64.b64decode(body.get('contentBase64', ''))
            except Exception:
                data = None
        else:
            try:
                data = request.bounded_stream.read()
            except Exception:
                data = None
        if not data or not filename:
            response.status = '400 Bad Request'
            response.media = {'ok': False,
                              'error': 'need a filename and file bytes '
                              '(JSON contentBase64 or raw body + ?filename=)'}
            return
        result = cad_import.import_cad(self.manager, filename, data, name=name)
        if not result.get('ok'):
            response.status = '502 Bad Gateway'
        response.media = result

    def on_post_export(self, request, response, name):
        body = request.media or {}
        fmt = body.get('format', 'glb')
        result = cad_import.export_shape(self.manager, name, fmt)
        if not result.get('ok'):
            response.status = '502 Bad Gateway'
        response.media = result

    def on_get_imports(self, request, response):
        table = (getattr(self.manager, 'objectTables', None) or {}).get(
            'ImportedCadObject', {})
        rows = list(table.values()) if isinstance(table, dict) \
            else list(table)
        response.media = {'ok': True, 'count': len(rows), 'imports': [{
            'name': getattr(r, 'name', ''),
            'sourceFilename': getattr(r, 'source_filename', ''),
            'sourceFormat': getattr(r, 'source_format', ''),
            'minioKey': getattr(r, 'minio_key', ''),
            'volumeCm3': getattr(r, 'volume_cm3', 0.0),
            'shapeName': getattr(r, 'shape_name', ''),
            'mesh3dName': getattr(r, 'mesh3d_name', ''),
            'importer': getattr(r, 'importer', ''),
        } for r in rows]}

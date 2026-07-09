"""
Selftest — shape-3: CAD import/export via the cad-engines worker + MinIO.

Run from polari-framework/:
    python3 -m mathshapes.selftest_shape3

Stdlib-only: the cad-engines worker HTTP seam and the MinIO object store
are both faked. Covers: an imported STL maps to shape + mesh + import
record rows carrying volume + bbox; the original is stored in MinIO;
capability is honest when the worker/store is absent; export samples the
shape (shape-1 sample_surface for math shapes, the cached mesh for
imported ones), calls the worker with the requested format, and stores
the artifact in MinIO; honest refusals when the worker or MinIO is
missing.
"""

import base64
import json
from types import SimpleNamespace

from mathshapes import cad_import, cad_minio

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


# ---- a fake cad-engines worker (records calls) ----
_TETRA_PTS = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
_TETRA_TRIS = [[0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]]


class FakeRemote:
    def __init__(self, worker_alive=True):
        self.worker_alive = worker_alive
        self.calls = []

    def remote_capability(self):
        if not self.worker_alive:
            return None
        return {'ok': True, 'trimesh': True, 'freecad': False,
                'importFormats': ['stl'], 'exportFormats': ['glb', 'stl',
                                                             'three-json']}

    def remote_post(self, path, payload):
        self.calls.append((path, payload))
        if not self.worker_alive:
            return {'ok': False, 'error': 'worker down',
                    'suggestion': self.unavailable_suggestion('down')}
        if path == '/cad/import':
            return {'ok': True, 'importer': 'trimesh', 'volume': 1.0 / 6.0,
                    'bbox': [[0, 1], [0, 1], [0, 1]],
                    'centroid': [0.25, 0.25, 0.25],
                    'meshPoints': _TETRA_PTS, 'triangles': _TETRA_TRIS,
                    'parametricParams': {'width': 10.0}}
        if path == '/cad/export':
            blob = base64.b64encode(b'FAKE-EXPORT-BYTES').decode()
            return {'ok': True, 'format': payload.get('format'),
                    'filename': 'shape.' + payload.get('format'),
                    'contentType': 'application/octet-stream',
                    'contentBase64': blob}
        return {'ok': False, 'error': 'unknown path'}

    def unavailable_suggestion(self, evidence):
        return {'evidence': evidence, 'knob': 'CAD_ENGINES_URL'}


# ---- a fake MinIO store (records puts) ----
class FakeMinioClient:
    def __init__(self):
        self.puts = []

    def put_object(self, bucket, key, stream, length, content_type=None):
        self.puts.append((bucket, key, length, content_type))

    def presigned_get_object(self, bucket, key, expires=None):
        return f'https://s3.local/{bucket}/{key}?sig=fake'


class FakeStore:
    def __init__(self):
        self.connected = True
        self.client = FakeMinioClient()
        self.endpoint = 's3.local'
        self.made = []

    def ensure_bucket(self, bucket):
        self.made.append(bucket)
        return True


def _fake_factory(manager, class_name, attrs):
    row = SimpleNamespace(**attrs)
    manager.objectTables.setdefault(class_name, {})[attrs['name']] = row
    return row


def _mgr(store=True):
    return SimpleNamespace(
        objectTables={'MathShapeDefinition': {}},
        objectStore=FakeStore() if store else None)


if __name__ == '__main__':
    stl = b'solid fake\nendsolid fake\n'

    print('capability — honest when worker/store absent')
    cap_dead = cad_import.capability(_mgr(store=False),
                                     remote=FakeRemote(worker_alive=False))
    check('no worker + no store -> capability ok False',
          not cap_dead['ok'] and not cap_dead['worker'].get('ok')
          and not cap_dead['minio']['ok'])
    cap_live = cad_import.capability(_mgr(store=True),
                                     remote=FakeRemote(worker_alive=True))
    check('live worker + live store -> capability ok True',
          cap_live['ok'] and cap_live['minio']['ok'])

    print('import — worker -> MinIO -> rows')
    mgr = _mgr(store=True)
    remote = FakeRemote()
    res = cad_import.import_cad(mgr, 'bracket-v2.stl', stl,
                               factory=_fake_factory, remote=remote)
    check('import ok', res.get('ok'), str(res.get('error', '')))
    check('worker /cad/import called with base64 of the file',
          any(p == '/cad/import'
              and base64.b64decode(pl['contentBase64']) == stl
              for p, pl in remote.calls))
    shape = mgr.objectTables['MathShapeDefinition'].get('bracket-v2-shape')
    mesh = mgr.objectTables['Mesh3DDefinition'].get('bracket-v2-mesh')
    rec = mgr.objectTables['ImportedCadObject'].get('bracket-v2-import')
    check('math shape row created (family imported-mesh)',
          shape is not None and shape.family == 'imported-mesh')
    check('render mesh row created (three-json + inline geometry)',
          mesh is not None and mesh.source == 'three-json'
          and 'BufferGeometry' in mesh.inline_definition)
    check('import record carries volume + bbox + params',
          rec is not None and abs(rec.volume_cm3 - 1.0 / 6.0) < 1e-6
          and json.loads(rec.parametric_params_json).get('width') == 10.0)
    check('original STORED in MinIO cad-imports bucket',
          any(b == cad_minio.IMPORT_BUCKET for b, k, ln, ct
              in mgr.objectStore.client.puts))
    check('result names the minio key + vertex count',
          res['vertexCount'] == 4 and 'cad-imports' in res['minioKey'])

    print('export — imported mesh (cached) -> worker -> MinIO')
    remote2 = FakeRemote()
    exp = cad_import.export_shape(mgr, 'bracket-v2-shape', 'glb',
                                  remote=remote2)
    check('export ok + names MinIO export key',
          exp.get('ok') and 'cad-exports' in exp['minioKey'])
    check('worker /cad/export called with format glb + the cached points',
          any(p == '/cad/export' and pl['format'] == 'glb'
              and pl['meshPoints'] == _TETRA_PTS for p, pl in remote2.calls))
    check('artifact stored in MinIO cad-exports bucket + download URL',
          any(b == cad_minio.EXPORT_BUCKET for b, k, ln, ct
              in mgr.objectStore.client.puts)
          and exp.get('downloadUrl'))

    print('export — a MATH shape samples its surface (shape-1)')
    mgr.objectTables['MathShapeDefinition']['ball'] = SimpleNamespace(
        name='ball', family='primitive', primitive_kind='sphere',
        parameters_json='{"radius": 1.0, "center": [0,0,0]}',
        quadric_matrix_json='', csg_json='', bounds_json='')
    remote3 = FakeRemote()
    exp2 = cad_import.export_shape(mgr, 'ball', 'three-json', remote=remote3)
    check('math-shape export ok (surface sampled, not cached)',
          exp2.get('ok')
          and any(p == '/cad/export' and len(pl['meshPoints']) > 0
                  for p, pl in remote3.calls))

    print('honest refusals')
    dead = cad_import.import_cad(_mgr(store=True), 'x.stl', stl,
                                factory=_fake_factory,
                                remote=FakeRemote(worker_alive=False))
    check('worker down -> import refuses (not ok, suggestion carried)',
          not dead.get('ok') and 'suggestion' in dead)
    nostore = cad_import.import_cad(_mgr(store=False), 'x.stl', stl,
                                   factory=_fake_factory, remote=FakeRemote())
    check('no MinIO -> import refuses at the store stage',
          not nostore.get('ok') and nostore.get('stage') == 'minio-store')

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)

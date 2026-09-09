"""
@module printing_suite.custom.adapters

The REAL adapters the API hands the pipeline (each refuses by returning
None / '' when its dependency is absent): the casting planner, mathshapes
shape export, an artifact cache (MinIO through mathshapes' cad_minio when
configured, else a local directory under the instance's data dir), the
Kiri:Moto CLI in the built container (docker on the host — so on a bare
container instance this adapter is absent and the slice step refuses),
and Moonraker's upload API on the printer guest.
"""
import hashlib
import json
import os
import subprocess
import tempfile
import urllib.request
import uuid

CACHE_DIR = os.environ.get('POLARI_PRINT_CACHE', '/data/printing-cache')


def build(manager):
    ctx = {}
    tables = getattr(manager, 'objectTables', None) or {}
    ctx['rows'] = lambda cls: list((tables.get(cls, {}) or {}).values())
    ctx['find_row'] = lambda cls, name: next((r for r in ctx['rows'](cls) if getattr(r, 'name', '') == name), None)
    def save(row):
        try:
            manager.db.saveInstanceInDB(row)
        except Exception:  # noqa: BLE001
            pass
    ctx['save'] = save
    import time
    ctx['now'] = lambda: time.strftime('%Y-%m-%dT%H:%M:%S')
    try:
        from casting.nesting_wizard_basis import plan_nesting
        ctx['plan_nesting'] = lambda part, target, feedstock: plan_nesting(manager, part, target, feedstock_name=feedstock)
    except Exception:  # noqa: BLE001
        pass
    try:
        from mathshapes.custom.cad_import import export_shape
        def _export(shape, fmt='stl'):
            r = export_shape(manager, shape, fmt)
            if isinstance(r, (bytes, bytearray)):
                return bytes(r)
            if isinstance(r, dict):
                if r.get('bytes'):
                    return r['bytes']
                if r.get('ok') and (r.get('minio_key') or r.get('key')):
                    from mathshapes.custom import cad_minio
                    return cad_minio.get_bytes(manager, r.get('minio_key') or r.get('key'), r.get('bucket', cad_minio.EXPORT_BUCKET))
            return b''
        ctx['export_shape'] = _export
    except Exception:  # noqa: BLE001
        pass
    # cache: MinIO when the store answers, else the data dir
    def cache_put(key, data):
        try:
            from mathshapes.custom.cad_minio import put_bytes, store_status
            if store_status(manager).get('ok'):
                put_bytes(manager, 'printing', key, data)
                return 'minio:printing/' + key
        except Exception:  # noqa: BLE001
            pass
        path = os.path.join(CACHE_DIR, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data)
        return 'file:' + path
    def cache_get(store_key):
        if store_key.startswith('file:'):
            return open(store_key[5:], 'rb').read()
        if store_key.startswith('minio:'):
            from mathshapes.custom.cad_minio import get_bytes
            bucket, key = store_key[6:].split('/', 1)
            return get_bytes(manager, key, bucket)
        return b''
    ctx['cache_put'] = cache_put
    ctx['cache_get'] = cache_get
    if _docker_image_present():
        ctx['slice_stl'] = slice_with_kirimoto
    ctx['printer_url'] = lambda printer: printer_url(ctx, printer)
    ctx['moonraker_upload'] = moonraker_upload
    return ctx


def _docker_image_present():
    try:
        from kirimoto.kirimoto_basis import KIRIMOTO_IMAGE
        r = subprocess.run(['docker', 'image', 'inspect', KIRIMOTO_IMAGE], capture_output=True, text=True, timeout=10)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def slice_with_kirimoto(stl_bytes, profile, slicer_profile):
    """Run Kiri:Moto's CLI (src/kiri/run/cli.js) in the built container with a
    device + process JSON derived from the profiles. Returns gcode bytes."""
    from kirimoto.kirimoto_basis import KIRIMOTO_IMAGE
    work = tempfile.mkdtemp(prefix='kiri-')
    open(os.path.join(work, 'model.stl'), 'wb').write(stl_bytes)
    device = {'bedWidth': slicer_profile.get('bed_x_mm', 350), 'bedDepth': slicer_profile.get('bed_y_mm', 350), 'maxHeight': slicer_profile.get('bed_z_mm', 340),
              'extruders': [{'extNozzle': profile.get('nozzle_mm', 0.4), 'extFilament': 1.75}], 'gcodeFlavor': slicer_profile.get('gcode_flavor', 'klipper')}
    process = {'sliceHeight': profile.get('layer_mm', 0.2), 'sliceShells': 3, 'sliceFillSparse': (profile.get('infill_pct', 20) or 20) / 100.0,
               'outputTemp': profile.get('nozzle_temp_c', 210), 'outputBedTemp': profile.get('bed_temp_c', 60), 'outputFeedrate': profile.get('speed_mm_s', 150),
               'outputRetractDist': profile.get('retraction_mm', 0.5), 'outputCoolingFan': profile.get('fan_pct', 100)}
    json.dump(device, open(os.path.join(work, 'device.json'), 'w'))
    json.dump(process, open(os.path.join(work, 'process.json'), 'w'))
    cmd = ['docker', 'run', '--rm', '-v', work + ':/work', KIRIMOTO_IMAGE, 'node', 'src/kiri/run/cli.js',
           '--dir=/grid', '--model=/work/model.stl', '--device=/work/device.json', '--process=/work/process.json', '--output=/work/out.gcode']
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    out = os.path.join(work, 'out.gcode')
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError('kirimoto cli failed: %s' % (r.stderr or r.stdout)[-300:])
    return open(out, 'rb').read()


def printer_url(ctx, printer):
    """http://<guest ip>:7125 from the voron guest's HardwareAppState (pushed by the isle)."""
    p = ctx['find_row']('PrinterDefinition', printer)
    guest = getattr(p, 'hardware_app', '') if p else ''
    for s in ctx['rows']('HardwareAppState'):
        if getattr(s, 'app', '') == guest and getattr(s, 'ip', ''):
            return 'http://%s:7125' % s.ip
    return ''


def moonraker_upload(url, filename, gcode, start=True):
    boundary = uuid.uuid4().hex
    body = b''.join([b'--' + boundary.encode() + b'\r\n',
                     b'Content-Disposition: form-data; name="root"\r\n\r\ngcodes\r\n',
                     b'--' + boundary.encode() + b'\r\n',
                     b'Content-Disposition: form-data; name="print"\r\n\r\n' + (b'true' if start else b'false') + b'\r\n',
                     b'--' + boundary.encode() + b'\r\n',
                     ('Content-Disposition: form-data; name="file"; filename="%s"\r\nContent-Type: application/octet-stream\r\n\r\n' % filename).encode(),
                     gcode, b'\r\n--' + boundary.encode() + b'--\r\n'])
    req = urllib.request.Request(url.rstrip('/') + '/server/files/upload', data=body, method='POST',
                                 headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            d = json.loads(resp.read() or b'{}')
            return {'ok': True, 'jobId': (d.get('result') or {}).get('item', {}).get('path', filename), 'sha256': hashlib.sha256(gcode).hexdigest()}
    except Exception as e:  # noqa: BLE001
        return {'ok': False, 'error': str(e)[:200]}

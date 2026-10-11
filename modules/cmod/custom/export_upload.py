"""
@module cmod.custom.export_upload

THE UPLOAD DOOR's work (POST /api/firmware/exports/upload, slice ucd-app): a host that built an installer the backend image
cannot build (it has no JDK) PUSHES the file here and gets a `FirmwareExport` row, so the demo page's Downloads table lists it
and anybody can fetch it from the same download door as every other export.

Body: multipart/form-data with fields `solution`, `form` (bridge-app-deb | shell-core-deb | demo-bundle | install-bundle), `sha256` and the file in `file`
(or a JSON body with the same names and the file as base64 in `file`, plus `filename`). The bytes are streamed to disk and hashed;
a sha256 that differs from the one given is refused (422) and nothing is kept.
"""
import base64
import datetime
import hashlib
import json
import os
import re

UPLOAD_FORMS = ('bridge-app-deb', 'shell-core-deb', 'demo-bundle', 'install-bundle')   # the bundles too: a host with mvn builds the jar and uploads (the backend image has no JDK)
_NAME = re.compile(r'[^A-Za-z0-9._+-]')
_SOL = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$')
_CHUNK = 1 << 20


class UploadRefused(Exception):
    def __init__(self, why, status=422):
        super().__init__(why)
        self.status = status


def _safe_filename(name):
    base = _NAME.sub('_', os.path.basename((name or '').replace('\\', '/')))
    return base.lstrip('.') or ''


def receive(request, root):
    """Parse + stream. -> (fields, tmp_path, sha256_of_bytes, nbytes). The file is written under `root` as a temp name."""
    os.makedirs(root, exist_ok=True)
    tmp = os.path.join(root, '.upload-%d.part' % os.getpid())
    fields, h, n = {}, hashlib.sha256(), 0
    ctype = (request.content_type or '').lower()
    try:
        if ctype.startswith('multipart/form-data'):
            form = request.get_media()
            got_file = False
            for part in form:
                if part.name == 'file':
                    fields['filename'] = fields.get('filename') or part.filename or ''
                    with open(tmp, 'wb') as out:
                        while True:
                            chunk = part.stream.read(_CHUNK)
                            if not chunk:
                                break
                            out.write(chunk)
                            h.update(chunk)
                            n += len(chunk)
                    got_file = True
                else:
                    fields[part.name] = (part.get_text() or '').strip()
            if not got_file:
                raise UploadRefused('no file field named `file` in the upload', 400)
        else:
            try:
                body = json.loads(request.bounded_stream.read() or b'{}')
                data = base64.b64decode(body.get('file', ''), validate=True)
            except Exception:  # noqa: BLE001
                raise UploadRefused('send multipart/form-data with a `file` part, or JSON with `file` as base64', 400)
            fields = {k: str(body.get(k, '')).strip() for k in ('solution', 'form', 'sha256', 'filename')}
            with open(tmp, 'wb') as out:
                out.write(data)
            h.update(data)
            n = len(data)
    except UploadRefused:
        _rm(tmp)
        raise
    except Exception as e:  # noqa: BLE001
        _rm(tmp)
        raise UploadRefused('the upload could not be read: %s' % e, 400)
    return fields, tmp, h.hexdigest(), n


def _rm(path):
    try:
        os.remove(path)
    except OSError:
        pass


def store(request, root):
    """Receive, check, and place the file. -> the FirmwareExport row fields. Raises UploadRefused (400 malformed, 422 sha)."""
    fields, tmp, got, n = receive(request, root)
    try:
        solution, form, want = fields.get('solution', ''), fields.get('form', ''), (fields.get('sha256', '') or '').lower()
        if not _SOL.match(solution):
            raise UploadRefused('`solution` is missing or not a plain name', 400)
        if form not in UPLOAD_FORMS:
            raise UploadRefused('`form` must be one of %s' % ' | '.join(UPLOAD_FORMS), 400)
        if not re.fullmatch(r'[0-9a-f]{64}', want):
            raise UploadRefused('`sha256` must be the file\'s 64-character sha256', 400)
        filename = _safe_filename(fields.get('filename', '')) or ('%s-%s.bin' % (solution, form))
        if got != want:
            raise UploadRefused('the file\'s sha256 (%s…) is not the one given (%s…); nothing was stored' % (got[:16], want[:16]), 422)
        stamp = datetime.datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
        name = '%s-%s@%s-%s' % (solution, form, stamp, got[:8])
        d = os.path.join(root, name)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, filename)
        os.replace(tmp, path)
    except UploadRefused:
        _rm(tmp)
        raise
    return {'name': name, 'solution': solution, 'graph': '', 'board': '', 'form': form, 'target': 'none', 'mode': 'online',
            'path': path, 'tar_path': path, 'tar_sha256': got, 'files_json': json.dumps([{'file': filename, 'sha256': got, 'bytes': n}]),
            'makefile_sha256': '', 'cmake_sha256': '', 'parity': 'not-run', 'verify_log': '',
            'download_url': '/api/firmware/exports/%s/download' % name,
            'created_at': datetime.datetime.now().isoformat(timespec='seconds'), 'status': 'created', 'why': '',
            'notes': 'uploaded, sha256 verified on arrival'}

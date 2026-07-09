"""
@cross-cutting
@module mathshapes.cad_minio
@tags @xc:bindings

Thin MinIO helpers for CAD import/export, layered on the suite's
existing managedObjectStore (manager.objectStore — a minio.Minio
client). CAD originals land in the `cad-imports` bucket, exported
artifacts in `cad-exports`. Every helper degrades honestly: when the
store is absent/disconnected it returns {'ok': False, suggestion}
instead of raising, matching the capability-ladder discipline.
"""

import io

IMPORT_BUCKET = 'cad-imports'
EXPORT_BUCKET = 'cad-exports'


def _store(manager):
    store = getattr(manager, 'objectStore', None)
    if store is None or not getattr(store, 'connected', False) \
            or getattr(store, 'client', None) is None:
        return None
    return store


def store_status(manager):
    store = _store(manager)
    if store is None:
        return {'ok': False, 'connected': False,
                'error': 'object store (MinIO) not connected',
                'suggestion': {'knob': 'MINIO_ENDPOINT / object storage '
                               'connection (ObjectStorageAPI)',
                               'action': 'connect the object store so CAD '
                               'originals + exports can be persisted'}}
    return {'ok': True, 'connected': True,
            'endpoint': getattr(store, 'endpoint', '')}


def put_bytes(manager, bucket, key, data, content_type='application/octet-stream'):
    """Store bytes; returns {'ok', key, bucket} or honest refusal."""
    store = _store(manager)
    if store is None:
        return store_status(manager)
    try:
        store.ensure_bucket(bucket)
        store.client.put_object(bucket, key, io.BytesIO(data), len(data),
                                content_type=content_type)
        return {'ok': True, 'bucket': bucket, 'key': key,
                'objectPath': f'{bucket}/{key}'}
    except Exception as e:
        return {'ok': False, 'error': f'MinIO put failed: {e}'}


def presigned_get(manager, bucket, key, expires_seconds=3600):
    """A time-limited download URL, or honest refusal."""
    store = _store(manager)
    if store is None:
        return store_status(manager)
    try:
        from datetime import timedelta
        url = store.client.presigned_get_object(
            bucket, key, expires=timedelta(seconds=expires_seconds))
        return {'ok': True, 'url': url, 'expiresSeconds': expires_seconds}
    except Exception as e:
        # presign can fail on some S3 backends; still hand back the key.
        return {'ok': False, 'error': f'presign failed: {e}',
                'objectPath': f'{bucket}/{key}'}

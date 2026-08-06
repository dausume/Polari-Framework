"""
@module appstore.appstore_minio

MinIO helpers for shell artifacts (the cad_minio idiom): one bucket,
a _store() guard, and honest {'ok': False, suggestion} refusals when
the object store is absent — a store page that says WHY there is no
download beats a stack trace.
"""

import io
from datetime import timedelta

ARTIFACT_BUCKET = 'shell-artifacts'


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
                'suggestion': {
                    'knob': 'MINIO_ENDPOINT / object storage '
                            'connection (ObjectStorageAPI)',
                    'action': 'connect the object store; shell '
                              'archives and prebuilt binaries live '
                              'in the shell-artifacts bucket'}}
    return {'ok': True, 'connected': True,
            'endpoint': getattr(store, 'endpoint', '')}


def get_bytes(manager, key, bucket=ARTIFACT_BUCKET):
    store = _store(manager)
    if store is None:
        return store_status(manager)
    try:
        resp = store.client.get_object(bucket, key)
        try:
            data = resp.read()
        finally:
            resp.close()
            resp.release_conn()
        return {'ok': True, 'data': data}
    except Exception as e:
        return {'ok': False,
                'error': f'MinIO get {bucket}/{key} failed: {e}'}


def object_exists(manager, key, bucket=ARTIFACT_BUCKET):
    store = _store(manager)
    if store is None:
        return store_status(manager)
    try:
        stat = store.client.stat_object(bucket, key)
        return {'ok': True, 'sizeBytes': stat.size}
    except Exception as e:
        return {'ok': False,
                'error': f'no object {bucket}/{key}: {e}'}


def presigned_get(manager, key, bucket=ARTIFACT_BUCKET,
                  expires_seconds=3600):
    store = _store(manager)
    if store is None:
        return store_status(manager)
    try:
        url = store.client.presigned_get_object(
            bucket, key, expires=timedelta(seconds=expires_seconds))
        return {'ok': True, 'url': url,
                'expiresSeconds': expires_seconds}
    except Exception as e:
        return {'ok': False, 'error': f'presign failed: {e}',
                'objectPath': f'{bucket}/{key}'}


def presigned_put(manager, key, bucket=ARTIFACT_BUCKET,
                  expires_seconds=3600):
    store = _store(manager)
    if store is None:
        return store_status(manager)
    try:
        store.ensure_bucket(bucket)
        url = store.client.presigned_put_object(
            bucket, key, expires=timedelta(seconds=expires_seconds))
        return {'ok': True, 'url': url,
                'expiresSeconds': expires_seconds,
                'objectPath': f'{bucket}/{key}'}
    except Exception as e:
        return {'ok': False, 'error': f'presign-put failed: {e}'}

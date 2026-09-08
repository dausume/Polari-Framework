"""
@module appstore.custom.appstore_minio

MinIO helpers for shell artifacts (the cad_minio idiom): one bucket,
a _store() guard, and honest {'ok': False, suggestion} refusals when
the object store is absent — a store page that says WHY there is no
download beats a stack trace.
"""

import io
import os
from datetime import timedelta
from urllib.parse import urlparse

ARTIFACT_BUCKET = 'shell-artifacts'


def _store(manager):
    store = getattr(manager, 'objectStore', None)
    if store is None or not getattr(store, 'connected', False) \
            or getattr(store, 'client', None) is None:
        return None
    return store


def _presign_client(manager):
    """Client to SIGN presigned URLs with. A URL signed against the
    internal endpoint (prf-file-store:9000) is useless outside the
    docker network — SigV4 binds the host, so rewriting breaks the
    signature (proven live). When a public S3 URL is declared
    (POLARI_S3_PUBLIC_URL, else MINIO_SERVER_URL — already in the
    backend env), sign against THAT host; signing is pure local
    crypto, no connection is made. Falls back to the internal
    client's URLs (still valid for in-network callers)."""
    store = _store(manager)
    if store is None:
        return None
    public = (os.environ.get('POLARI_S3_PUBLIC_URL')
              or os.environ.get('MINIO_SERVER_URL') or '').strip()
    if not public:
        return store.client
    try:
        from minio import Minio
        u = urlparse(public)
        # region pinned so minio-py SKIPS its get_bucket_location
        # round-trip — without it presign phones the public host
        # from inside the container (untrusted CA + hairpin, caught
        # live). MinIO's default region is us-east-1.
        return Minio(u.netloc,
                     access_key=getattr(store, 'access_key', ''),
                     secret_key=getattr(store, 'secret_key', ''),
                     secure=(u.scheme == 'https'),
                     region=os.environ.get(
                         'POLARI_S3_REGION', 'us-east-1'))
    except Exception:
        return store.client


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
    signer = _presign_client(manager)
    if signer is None:
        return store_status(manager)
    try:
        url = signer.presigned_get_object(
            bucket, key, expires=timedelta(seconds=expires_seconds))
        return {'ok': True, 'url': url,
                'expiresSeconds': expires_seconds}
    except Exception as e:
        return {'ok': False, 'error': f'presign failed: {e}',
                'objectPath': f'{bucket}/{key}'}


def presigned_put(manager, key, bucket=ARTIFACT_BUCKET,
                  expires_seconds=3600):
    store = _store(manager)
    signer = _presign_client(manager)
    if store is None or signer is None:
        return store_status(manager)
    try:
        store.ensure_bucket(bucket)
        url = signer.presigned_put_object(
            bucket, key, expires=timedelta(seconds=expires_seconds))
        return {'ok': True, 'url': url,
                'expiresSeconds': expires_seconds,
                'objectPath': f'{bucket}/{key}'}
    except Exception as e:
        return {'ok': False, 'error': f'presign-put failed: {e}'}

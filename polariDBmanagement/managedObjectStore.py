"""
Managed Object Store — MinIO/S3-compatible object storage connection manager.

Mirrors the managedDatabase pattern: can be initialized at startup if configured,
or connected dynamically via the ObjectStorageAPI.
"""

import os
import time
from objectTreeDecorators import treeObject, treeObjectInit


class managedObjectStore(treeObject):
    """Manages connection to MinIO/S3-compatible object storage."""

    @treeObjectInit
    def __init__(self, endpoint='', access_key='', secret_key='', secure=False,
                 public_endpoint='', public_secure=None, manager=None):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        # Presigned URLs are handed to a BROWSER, which can't resolve the
        # internal Docker network address (endpoint, e.g. pol-file-store:9000)
        # — they need the same public host anything else browser-reachable
        # uses (MINIO_PUBLIC_URL, e.g. https://s3.<domain> in staging/prod,
        # http://localhost:9000 in dev). Presign signatures include the Host
        # header, so this must be a SEPARATE client built against that host
        # — swapping the hostname in an already-signed URL breaks the
        # signature. Falls back to `endpoint` (dev-without-the-var case)
        # rather than failing outright.
        self.public_endpoint = public_endpoint or endpoint
        self.public_secure = secure if public_secure is None else public_secure
        self.client = None
        self._presign_client_cache = None
        self.connected = False
        self.buckets = []
        if endpoint and access_key and secret_key:
            self._connect()

    def _connect(self):
        """Attempt to connect to MinIO and verify connection."""
        try:
            from minio import Minio
            # region pinned (MinIO's own default) so presigning never needs a
            # live GetBucketLocation lookup — that lookup would otherwise run
            # against whichever host generates the URL, including the public
            # HTTPS endpoint from _presign_client(), which fails on the
            # self-signed staging CA the container doesn't trust.
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
                region='us-east-1',
            )
            # Verify connection by listing buckets
            bucket_list = [b.name for b in self.client.list_buckets()]
            self.buckets = bucket_list
            self.connected = True
        except Exception as e:
            print(f'[managedObjectStore] Connection failed: {e}')
            self.client = None
            self.connected = False

    def disconnect(self):
        """Disconnect from object storage."""
        self.client = None
        self.connected = False
        self.buckets = []

    def test_connection(self) -> dict:
        """Test connection and return status dict."""
        start = time.time()
        try:
            if self.client is None:
                return {
                    'connected': False,
                    'endpoint': self.endpoint,
                    'latency': 0,
                    'error': 'No client initialized'
                }
            self.client.list_buckets()
            latency = round((time.time() - start) * 1000, 2)
            return {
                'connected': True,
                'endpoint': self.endpoint,
                'latency': latency,
                'error': None
            }
        except Exception as e:
            latency = round((time.time() - start) * 1000, 2)
            return {
                'connected': False,
                'endpoint': self.endpoint,
                'latency': latency,
                'error': str(e)
            }

    def ensure_bucket(self, bucket_name) -> bool:
        """Create bucket if it doesn't exist. Returns True on success."""
        if not self.connected or self.client is None:
            return False
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
            if bucket_name not in self.buckets:
                self.buckets.append(bucket_name)
            return True
        except Exception as e:
            print(f'[managedObjectStore] ensure_bucket failed: {e}')
            return False

    def upload_file(self, bucket, object_name, file_path, content_type=None) -> str:
        """Upload a local file. Returns the object path (bucket/object_name)."""
        if not self.connected or self.client is None:
            raise RuntimeError('Object store not connected')
        self.ensure_bucket(bucket)
        if content_type:
            self.client.fput_object(bucket, object_name, file_path, content_type=content_type)
        else:
            self.client.fput_object(bucket, object_name, file_path)
        return f'{bucket}/{object_name}'

    def download_file(self, bucket, object_name, local_path) -> str:
        """Download an object to a local file. Returns local path."""
        if not self.connected or self.client is None:
            raise RuntimeError('Object store not connected')
        self.client.fget_object(bucket, object_name, local_path)
        return local_path

    def list_objects(self, bucket, prefix='') -> list:
        """List every object in a bucket (optionally under a prefix),
        including nested "subdirectories" (recursive) — a non-recursive
        listing only returns direct children and groups anything nested
        as an opaque common-prefix, silently hiding objects from callers
        that just want a flat enumeration (e.g. remove_prefix cleanup)."""
        if not self.connected or self.client is None:
            return []
        try:
            objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
            return [
                {
                    'name': obj.object_name,
                    'size': obj.size,
                    'lastModified': str(obj.last_modified) if obj.last_modified else None
                }
                for obj in objects
            ]
        except Exception as e:
            print(f'[managedObjectStore] list_objects failed: {e}')
            return []

    def remove_object(self, bucket, object_name) -> bool:
        """Delete a single object. Returns True on success (also True if
        the object never existed — deletion is idempotent)."""
        if not self.connected or self.client is None:
            return False
        try:
            self.client.remove_object(bucket, object_name)
            return True
        except Exception as e:
            print(f'[managedObjectStore] remove_object failed: {e}')
            return False

    def remove_prefix(self, bucket, prefix) -> int:
        """Delete every object under a prefix (e.g. an asset's HLS
        segment tree). Returns the count actually removed."""
        if not self.connected or self.client is None:
            return 0
        removed = 0
        for entry in self.list_objects(bucket, prefix=prefix):
            if self.remove_object(bucket, entry['name']):
                removed += 1
        return removed

    def _presign_client(self):
        """The Minio client used ONLY for presigning — built against the
        public-facing endpoint so the resulting URL's Host (part of the
        SigV4-signed request) matches what the browser will actually send.
        Lazily constructed; falls back to the main client when the public
        endpoint equals the internal one (nothing to gain from a second
        client)."""
        if self.public_endpoint == self.endpoint and self.public_secure == self.secure:
            return self.client
        if self._presign_client_cache is None:
            from minio import Minio
            self._presign_client_cache = Minio(
                self.public_endpoint, access_key=self.access_key,
                secret_key=self.secret_key, secure=self.public_secure,
                region='us-east-1')
        return self._presign_client_cache

    def presigned_put_url(self, bucket, object_name, expires_seconds=3600) -> str:
        """A time-limited URL a browser can PUT an object to directly,
        without routing the file's bytes through this backend."""
        if not self.connected or self.client is None:
            raise RuntimeError('Object store not connected')
        from datetime import timedelta
        self.ensure_bucket(bucket)
        return self._presign_client().presigned_put_object(
            bucket, object_name, expires=timedelta(seconds=expires_seconds))

    def presigned_get_url(self, bucket, object_name, expires_seconds=3600) -> str:
        """A time-limited URL to GET a (non-public) object directly from
        the store, without routing its bytes through this backend."""
        if not self.connected or self.client is None:
            raise RuntimeError('Object store not connected')
        from datetime import timedelta
        return self._presign_client().presigned_get_object(
            bucket, object_name, expires=timedelta(seconds=expires_seconds))

    def set_public_read_policy(self, bucket_name) -> bool:
        """Anonymous read-only (GET, no listing) on a bucket. Used for
        content meant to be served directly to a browser via the proxied
        s3 endpoint — e.g. HLS manifests/segments, where presigning every
        segment individually isn't practical. Returns True on success."""
        if not self.connected or self.client is None:
            return False
        import json as _json
        policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow', 'Principal': {'AWS': ['*']},
                'Action': ['s3:GetObject'],
                'Resource': [f'arn:aws:s3:::{bucket_name}/*'],
            }],
        }
        try:
            self.client.set_bucket_policy(bucket_name, _json.dumps(policy))
            return True
        except Exception as e:
            print(f'[managedObjectStore] set_public_read_policy failed: {e}')
            return False

    def list_buckets(self) -> list:
        """List all buckets. Caches result in self.buckets."""
        if not self.connected or self.client is None:
            return []
        try:
            bucket_list = [b.name for b in self.client.list_buckets()]
            self.buckets = bucket_list
            return self.buckets
        except Exception as e:
            print(f'[managedObjectStore] list_buckets failed: {e}')
            return []

    def get_status(self) -> dict:
        """Return current connection status for API responses."""
        return {
            'connected': self.connected,
            'endpoint': self.endpoint,
            'secure': self.secure,
            'buckets': self.buckets,
            'error': None if self.connected else 'Not connected'
        }

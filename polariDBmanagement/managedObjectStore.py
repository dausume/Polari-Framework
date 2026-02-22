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
    def __init__(self, endpoint='', access_key='', secret_key='', secure=False, manager=None):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.client = None
        self.connected = False
        self.buckets = []
        if endpoint and access_key and secret_key:
            self._connect()

    def _connect(self):
        """Attempt to connect to MinIO and verify connection."""
        try:
            from minio import Minio
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
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
        """List objects in a bucket with optional prefix filter."""
        if not self.connected or self.client is None:
            return []
        try:
            objects = self.client.list_objects(bucket, prefix=prefix)
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

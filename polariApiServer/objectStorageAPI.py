#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Object Storage API

Provides endpoints for checking and managing MinIO/S3-compatible object
storage connections. Follows the systemInfoAPI pattern.

Routes:
    GET  /object-storage             - Connection status
    POST /object-storage/connect     - Connect with credentials
    POST /object-storage/disconnect  - Disconnect
    GET  /object-storage/buckets     - List buckets
    POST /object-storage/buckets     - Create a bucket
"""

from objectTreeDecorators import treeObject, treeObjectInit
import falcon
import os


class ObjectStorageAPI(treeObject):
    """API for checking and managing object storage (MinIO) connection."""

    @treeObjectInit
    def __init__(self, polServer, manager=None):
        self.polServer = polServer
        self.apiName = '/object-storage'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            polServer.falconServer.add_route(self.apiName + '/connect', self, suffix='connect')
            polServer.falconServer.add_route(self.apiName + '/disconnect', self, suffix='disconnect')
            polServer.falconServer.add_route(self.apiName + '/buckets', self, suffix='buckets')
            # fs-2: browsing AS THE CALLER — the realm token becomes temporary store keys (accessControl/store_identity)
            polServer.falconServer.add_route(self.apiName + '/browse', self, suffix='browse')
            polServer.falconServer.add_route(self.apiName + '/browse/{bucket}', self, suffix='browse_bucket')
            polServer.falconServer.add_route(self.apiName + '/browse/{bucket}/link', self, suffix='browse_link')

    def on_get(self, request, response):
        """GET /object-storage - Return connection status."""
        try:
            store = getattr(self.manager, 'objectStore', None)
            if store is not None:
                response.media = store.get_status()
            else:
                response.media = {
                    'connected': False,
                    'endpoint': None,
                    'secure': False,
                    'buckets': [],
                    'error': 'Object storage not initialized'
                }
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {'connected': False, 'error': str(err)}
        response.set_header('Powered-By', 'Polari')

    def on_post_connect(self, request, response):
        """POST /object-storage/connect - Connect/reconnect with credentials."""
        try:
            body = request.media or {}
            endpoint = body.get('endpoint', '')
            access_key = body.get('accessKey', '')
            secret_key = body.get('secretKey', '')
            secure = body.get('secure', False)
            # Optional — browser-reachable host for presigned URLs, when it
            # differs from `endpoint` (e.g. a manual reconnect against the
            # internal Docker address). Falls back to `endpoint` if omitted.
            public_endpoint = body.get('publicEndpoint', '')
            public_secure = body.get('publicSecure', None)

            if not endpoint or not access_key or not secret_key:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'endpoint, accessKey, and secretKey are required'}
                return

            from polariDBmanagement.managedObjectStore import managedObjectStore
            store = managedObjectStore(
                endpoint=endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
                public_endpoint=public_endpoint,
                public_secure=public_secure,
                manager=self.manager
            )

            if store.connected:
                self.manager.objectStore = store
                response.media = {'success': True, **store.get_status()}
            else:
                response.media = {'success': False, 'error': 'Failed to connect to object storage'}

            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(err)}
            print(f'[ObjectStorageAPI] Connect error: {err}')
        response.set_header('Powered-By', 'Polari')

    def on_post_disconnect(self, request, response):
        """POST /object-storage/disconnect - Disconnect from object storage."""
        try:
            store = getattr(self.manager, 'objectStore', None)
            if store is not None:
                store.disconnect()
                self.manager.objectStore = None
            response.media = {'success': True, 'connected': False}
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(err)}
        response.set_header('Powered-By', 'Polari')

    def on_get_buckets(self, request, response):
        """GET /object-storage/buckets - List available buckets."""
        try:
            store = getattr(self.manager, 'objectStore', None)
            if store is not None and store.connected:
                buckets = store.list_buckets()
                response.media = {'success': True, 'buckets': buckets}
            else:
                response.media = {'success': False, 'buckets': [], 'error': 'Object storage not connected'}
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(err)}
        response.set_header('Powered-By', 'Polari')

    def on_post_buckets(self, request, response):
        """POST /object-storage/buckets - Create a new bucket."""
        try:
            body = request.media or {}
            bucket_name = body.get('name', '')
            if not bucket_name:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'Bucket name is required'}
                return

            store = getattr(self.manager, 'objectStore', None)
            if store is not None and store.connected:
                created = store.ensure_bucket(bucket_name)
                response.media = {'success': created, 'bucket': bucket_name}
            else:
                response.media = {'success': False, 'error': 'Object storage not connected'}
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(err)}
        response.set_header('Powered-By', 'Polari')

    # ------------------------------------------------------------------ fs-2: browse as the caller
    # The store's own browser UI is closed (it had no login). These routes are the Polari door: anonymous → 401,
    # a signed-in person → its realm token exchanged for temporary store keys, so the STORE applies the person's
    # roles (a viewer lists and reads, never writes); when the store has no OIDC door the backend applies the
    # same role table (the answer says which — `who.enforced_by`). Every listing is capped and says so.

    @staticmethod
    def _int(request, name, default, cap):
        try:
            return max(1, min(cap, int(request.get_param(name) or default)))
        except Exception:
            return default

    @staticmethod
    def _presign(caller, bucket, key, expires_s):
        from datetime import timedelta
        try:
            return caller.presign_client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires_s))
        except Exception as exc:
            return 'presign failed: %s' % exc

    def _list_objects(self, caller, bucket, prefix, limit, expires_s, with_links=True):
        rows, truncated = [], False
        for obj in caller.client.list_objects(bucket, prefix=prefix or '', recursive=True):
            if len(rows) >= limit:
                truncated = True
                break
            row = {'bucket': bucket, 'key': obj.object_name, 'size_bytes': obj.size,
                   'modified': obj.last_modified.strftime('%Y-%m-%dT%H:%M:%SZ') if obj.last_modified else None,
                   'content_type': getattr(obj, 'content_type', None) or ''}
            if with_links:
                row['link'] = self._presign(caller, bucket, obj.object_name, expires_s)
            rows.append(row)
        return rows, truncated

    def on_get_browse(self, request, response):
        """GET /object-storage/browse[?objects=1&limit=200&prefix=&expires=3600] — the caller's buckets; with
        objects=1 every object across them (flat rows, capped) with a time-limited download link each."""
        from accessControl.store_identity import caller_store_client
        from minio.error import S3Error
        caller = caller_store_client(self.manager, request, verb='read')
        want_objects = str(request.get_param('objects') or '').lower() in ('1', 'yes', 'true')
        limit = self._int(request, 'limit', 200, 2000)
        expires_s = self._int(request, 'expires', 3600, 7 * 24 * 3600)
        prefix = request.get_param('prefix') or ''
        try:
            buckets = [{'bucket': b.name, 'created': b.creation_date.strftime('%Y-%m-%dT%H:%M:%SZ') if b.creation_date else None} for b in caller.client.list_buckets()]
        except S3Error as err:
            response.status = falcon.HTTP_403 if err.code in ('AccessDenied', 'InvalidAccessKeyId') else falcon.HTTP_502
            response.media = {'ok': False, 'error': '%s: %s' % (err.code, err.message), 'who': caller.who}
            return
        out = {'ok': True, 'who': caller.who, 'buckets': buckets, 'bucket_count': len(buckets),
               'note': 'buckets the store lets you see; ?objects=1 lists their objects (capped by ?limit=, default 200 per bucket) with download links that expire (?expires= seconds, default 3600)'}
        if want_objects:
            objects, denied, truncated = [], [], []
            for b in buckets:
                try:
                    rows, more = self._list_objects(caller, b['bucket'], prefix, limit, expires_s)
                except S3Error as err:
                    denied.append('%s (%s)' % (b['bucket'], err.code))
                    continue
                objects.extend(rows)
                if more:
                    truncated.append(b['bucket'])
            out.update({'objects': objects, 'object_count': len(objects), 'truncated_buckets': truncated, 'denied_buckets': denied})
        response.status = falcon.HTTP_200
        response.media = out
        response.set_header('Powered-By', 'Polari')

    def on_get_browse_bucket(self, request, response, bucket):
        """GET /object-storage/browse/{bucket}[?prefix=&limit=500&expires=3600] — one bucket's objects, as the caller."""
        from accessControl.store_identity import caller_store_client
        from minio.error import S3Error
        caller = caller_store_client(self.manager, request, verb='read')
        limit = self._int(request, 'limit', 500, 5000)
        expires_s = self._int(request, 'expires', 3600, 7 * 24 * 3600)
        prefix = request.get_param('prefix') or ''
        try:
            rows, truncated = self._list_objects(caller, bucket, prefix, limit, expires_s)
        except S3Error as err:
            response.status = falcon.HTTP_404 if err.code == 'NoSuchBucket' else (falcon.HTTP_403 if err.code == 'AccessDenied' else falcon.HTTP_502)
            response.media = {'ok': False, 'bucket': bucket, 'error': '%s: %s' % (err.code, err.message), 'who': caller.who}
            return
        response.status = falcon.HTTP_200
        response.media = {'ok': True, 'who': caller.who, 'bucket': bucket, 'prefix': prefix, 'objects': rows, 'object_count': len(rows), 'truncated': truncated,
                          'note': 'each link is a time-limited signed URL minted with YOUR keys (default 3600 s); the store checks it, not the backend'}
        response.set_header('Powered-By', 'Polari')

    def on_get_browse_link(self, request, response, bucket):
        """GET /object-storage/browse/{bucket}/link?key=<object>[&expires=3600] — one time-limited download link; ?go=1 redirects to it."""
        from accessControl.store_identity import caller_store_client
        caller = caller_store_client(self.manager, request, verb='read')
        key = request.get_param('key') or ''
        if not key:
            raise falcon.HTTPBadRequest(title='key required', description='?key=<object name>')
        expires_s = self._int(request, 'expires', 3600, 7 * 24 * 3600)
        url = self._presign(caller, bucket, key, expires_s)
        if url.startswith('presign failed'):
            response.status = falcon.HTTP_502
            response.media = {'ok': False, 'bucket': bucket, 'key': key, 'error': url, 'who': caller.who}
            return
        if str(request.get_param('go') or '').lower() in ('1', 'yes', 'true'):
            raise falcon.HTTPFound(url)
        response.status = falcon.HTTP_200
        response.media = {'ok': True, 'who': caller.who, 'bucket': bucket, 'key': key, 'link': url, 'expires_s': expires_s}
        response.set_header('Powered-By', 'Polari')

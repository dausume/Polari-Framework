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

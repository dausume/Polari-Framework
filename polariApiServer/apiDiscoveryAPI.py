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
API Discovery Endpoint

Provides a comprehensive list of all available API endpoints,
including CRUDE endpoints for registered object types.
"""

from objectTreeDecorators import treeObject, treeObjectInit
import falcon


class APIDiscoveryAPI(treeObject):
    """
    Endpoint: /api-discovery

    Returns a list of all available API endpoints on the server.
    """

    @treeObjectInit
    def __init__(self, polServer, manager=None, **kwargs):
        self.polServer = polServer
        self.apiName = '/api-discovery'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response):
        """
        Get all available API endpoints.

        Response:
        {
            "success": true,
            "crudeEndpoints": [
                {
                    "objectType": "TestObject",
                    "endpoint": "/TestObject",
                    "methods": ["GET", "POST", "PUT", "DELETE"],
                    "instanceCount": 5
                }
            ],
            "customEndpoints": [
                {
                    "name": "/apiProfiler/query",
                    "type": "custom"
                }
            ],
            "systemEndpoints": [...]
        }
        """
        try:
            result = {
                'success': True,
                'crudeEndpoints': [],
                'customEndpoints': [],
                'systemEndpoints': []
            }

            # Get CRUDE endpoints (object type APIs)
            if hasattr(self.polServer, 'crudObjectsList'):
                for crude in self.polServer.crudObjectsList:
                    endpoint_info = {
                        'objectType': crude.apiObject,
                        'endpoint': crude.apiName,
                        'methods': ['GET', 'POST', 'PUT', 'DELETE'],
                        'instanceCount': len(self.manager.objectTables.get(crude.apiObject, {})) if hasattr(self.manager, 'objectTables') else 0
                    }

                    # Get typing info if available
                    if hasattr(self.manager, 'objectTypingDict') and crude.apiObject in self.manager.objectTypingDict:
                        typing_obj = self.manager.objectTypingDict[crude.apiObject]
                        endpoint_info['displayName'] = getattr(typing_obj, 'displayName', crude.apiObject)
                        endpoint_info['isStateSpaceObject'] = getattr(typing_obj, 'isStateSpaceObject', False)

                    result['crudeEndpoints'].append(endpoint_info)

            # Get custom APIs
            if hasattr(self.polServer, 'customAPIsList'):
                for api in self.polServer.customAPIsList:
                    if hasattr(api, 'apiName'):
                        api_info = {
                            'name': api.apiName,
                            'type': type(api).__name__
                        }
                        result['customEndpoints'].append(api_info)

            # System endpoints
            result['systemEndpoints'] = [
                {'name': '/', 'description': 'Server touchpoint'},
                {'name': '/login', 'description': 'Authentication'},
                {'name': '/register', 'description': 'User registration'},
                {'name': '/managerObject', 'description': 'Manager metadata'},
                {'name': '/typing-analysis', 'description': 'Type analysis'},
                {'name': '/stateSpaceClasses', 'description': 'State space classes'},
                {'name': '/classInstanceCounts', 'description': 'Instance counts'},
                {'name': '/api-discovery', 'description': 'This endpoint'}
            ]

            # Summary
            result['summary'] = {
                'totalCrudeEndpoints': len(result['crudeEndpoints']),
                'totalCustomEndpoints': len(result['customEndpoints']),
                'totalSystemEndpoints': len(result['systemEndpoints'])
            }

            response.status = falcon.HTTP_200
            response.media = result

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

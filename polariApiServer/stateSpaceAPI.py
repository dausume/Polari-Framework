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
State-Space API Endpoints

Provides endpoints for:
- Retrieving state-space enabled classes
- Managing state definitions
- Getting state-space configuration for classes
"""

from objectTreeDecorators import treeObject, treeObjectInit
from polariDataTyping.stateDefinition import StateDefinition, create_state_definition_from_event
import falcon
import json


class StateSpaceClassesAPI(treeObject):
    """
    API endpoint to retrieve all classes that are enabled for state-space (no-code) use.
    GET /stateSpaceClasses - Returns list of state-space enabled classes with their config
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/stateSpaceClasses'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response):
        """Get all state-space enabled classes"""
        try:
            state_space_classes = []

            # Iterate through all object typings and find state-space enabled ones
            for className, polyTypedObj in self.manager.objectTypingDict.items():
                if getattr(polyTypedObj, 'isStateSpaceObject', False):
                    state_space_classes.append(polyTypedObj.getStateSpaceConfig())

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'stateSpaceClasses': state_space_classes,
                'count': len(state_space_classes)
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')


class StateSpaceConfigAPI(treeObject):
    """
    API endpoint to get/update state-space configuration for a specific class.
    GET /stateSpaceConfig/{className} - Get state-space config for a class
    PUT /stateSpaceConfig/{className} - Update state-space config for a class
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/stateSpaceConfig/{className}'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_get(self, request, response, className):
        """Get state-space configuration for a specific class"""
        try:
            polyTypedObj = self.manager.objectTypingDict.get(className)

            if not polyTypedObj:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Class {className} not found'}
                return

            if not getattr(polyTypedObj, 'isStateSpaceObject', False):
                response.status = falcon.HTTP_400
                response.media = {
                    'success': False,
                    'error': f'Class {className} is not enabled for state-space'
                }
                return

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'config': polyTypedObj.getStateSpaceConfig()
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')

    def on_put(self, request, response, className):
        """Update state-space configuration for a class"""
        try:
            raw_data = request.bounded_stream.read()
            config = json.loads(raw_data.decode('utf-8'))

            polyTypedObj = self.manager.objectTypingDict.get(className)

            if not polyTypedObj:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Class {className} not found'}
                return

            if not getattr(polyTypedObj, 'allowClassEdit', False):
                response.status = falcon.HTTP_403
                response.media = {
                    'success': False,
                    'error': f'Class {className} does not allow editing'
                }
                return

            # Update state-space settings
            if 'isStateSpaceObject' in config:
                polyTypedObj.isStateSpaceObject = config['isStateSpaceObject']

            if 'displayFields' in config:
                fields_per_row = config.get('fieldsPerRow', 1)
                polyTypedObj.setStateSpaceDisplayFields(config['displayFields'], fields_per_row)

            if 'fieldsPerRow' in config and 'displayFields' not in config:
                polyTypedObj.stateSpaceFieldsPerRow = max(1, min(2, config['fieldsPerRow']))

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'config': polyTypedObj.getStateSpaceConfig()
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')


class StateDefinitionAPI(treeObject):
    """
    API endpoint for managing state definitions.
    GET /stateDefinitions - List all state definitions
    POST /stateDefinitions - Create a new state definition
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/stateDefinitions'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)
            # Also register the single-item endpoint
            polServer.falconServer.add_route('/stateDefinition/{definitionId}', self, suffix='single')

        # Store state definitions (in production, would use database)
        self.stateDefinitions = {}

    def on_get(self, request, response):
        """List all state definitions"""
        try:
            # Optional filter by class name
            class_filter = request.get_param('className')

            definitions = []
            for def_id, state_def in self.stateDefinitions.items():
                if class_filter and state_def.source_class_name != class_filter:
                    continue
                definitions.append(state_def.to_dict())

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'stateDefinitions': definitions,
                'count': len(definitions)
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')

    def on_post(self, request, response):
        """Create a new state definition"""
        try:
            raw_data = request.bounded_stream.read()
            data = json.loads(raw_data.decode('utf-8'))

            # Validate required fields
            if not data.get('name'):
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'name is required'}
                return

            if not data.get('sourceClassName'):
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'sourceClassName is required'}
                return

            # Verify source class exists and is state-space enabled
            source_class = data['sourceClassName']
            polyTypedObj = self.manager.objectTypingDict.get(source_class)

            if not polyTypedObj:
                response.status = falcon.HTTP_404
                response.media = {
                    'success': False,
                    'error': f'Source class {source_class} not found'
                }
                return

            if not getattr(polyTypedObj, 'isStateSpaceObject', False):
                response.status = falcon.HTTP_400
                response.media = {
                    'success': False,
                    'error': f'Class {source_class} is not enabled for state-space'
                }
                return

            # Create the state definition
            state_def = StateDefinition.from_dict(data, manager=self.manager)

            # If an event method is specified, auto-generate slots
            if data.get('eventMethodName') and not data.get('inputSlots') and not data.get('outputSlots'):
                state_def.generate_slots_from_event(polyTypedObj)

            # Validate
            is_valid, errors = state_def.validate()
            if not is_valid:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'errors': errors}
                return

            # Store the definition
            self.stateDefinitions[state_def.id] = state_def

            response.status = falcon.HTTP_201
            response.media = {
                'success': True,
                'stateDefinition': state_def.to_dict()
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

    def on_get_single(self, request, response, definitionId):
        """Get a single state definition by ID"""
        try:
            state_def = self.stateDefinitions.get(definitionId)

            if not state_def:
                response.status = falcon.HTTP_404
                response.media = {
                    'success': False,
                    'error': f'State definition {definitionId} not found'
                }
                return

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'stateDefinition': state_def.to_dict()
            }

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')

    def on_put_single(self, request, response, definitionId):
        """Update a state definition"""
        try:
            state_def = self.stateDefinitions.get(definitionId)

            if not state_def:
                response.status = falcon.HTTP_404
                response.media = {
                    'success': False,
                    'error': f'State definition {definitionId} not found'
                }
                return

            raw_data = request.bounded_stream.read()
            data = json.loads(raw_data.decode('utf-8'))

            # Update fields
            if 'displayName' in data:
                state_def.display_name = data['displayName']
            if 'description' in data:
                state_def.description = data['description']
            if 'category' in data:
                state_def.category = data['category']
            if 'color' in data:
                state_def.color = data['color']
            if 'icon' in data:
                state_def.icon = data['icon']
            if 'fieldsPerRow' in data:
                state_def.set_fields_per_row(data['fieldsPerRow'])

            # Validate
            is_valid, errors = state_def.validate()
            if not is_valid:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'errors': errors}
                return

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'stateDefinition': state_def.to_dict()
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')

    def on_delete_single(self, request, response, definitionId):
        """Delete a state definition"""
        try:
            if definitionId not in self.stateDefinitions:
                response.status = falcon.HTTP_404
                response.media = {
                    'success': False,
                    'error': f'State definition {definitionId} not found'
                }
                return

            del self.stateDefinitions[definitionId]

            response.status = falcon.HTTP_200
            response.media = {'success': True, 'deleted': definitionId}

        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')

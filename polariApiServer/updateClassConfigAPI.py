from objectTreeDecorators import treeObject, treeObjectInit
import falcon
import json


class UpdateClassConfigAPI(treeObject):
    """
    API endpoint to update polyTypedObject config flags for a class.
    POST /updateClassConfig - Update config flags like isStateSpaceObject, allowClassEdit, excludeFromCRUDE
    """

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/updateClassConfig'
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def on_post(self, request, response):
        """Update configuration flags for a class"""
        try:
            data = request.get_media()

            className = data.get('className')
            if not className:
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'className is required'}
                return

            config = data.get('config')
            if not config or not isinstance(config, dict):
                response.status = falcon.HTTP_400
                response.media = {'success': False, 'error': 'config object is required'}
                return

            polyTypedObj = self.manager.objectTypingDict.get(className)
            if not polyTypedObj:
                response.status = falcon.HTTP_404
                response.media = {'success': False, 'error': f'Class {className} not found'}
                return

            # Update supported config flags
            if 'isStateSpaceObject' in config:
                polyTypedObj.isStateSpaceObject = bool(config['isStateSpaceObject'])

            if 'allowClassEdit' in config:
                polyTypedObj.allowClassEdit = bool(config['allowClassEdit'])

            if 'excludeFromCRUDE' in config:
                polyTypedObj.excludeFromCRUDE = bool(config['excludeFromCRUDE'])

            # Build response config from current state
            response_config = {
                'isStateSpaceObject': getattr(polyTypedObj, 'isStateSpaceObject', False),
                'allowClassEdit': getattr(polyTypedObj, 'allowClassEdit', False),
                'excludeFromCRUDE': getattr(polyTypedObj, 'excludeFromCRUDE', False),
            }

            response.status = falcon.HTTP_200
            response.media = {
                'success': True,
                'className': className,
                'config': response_config
            }

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')

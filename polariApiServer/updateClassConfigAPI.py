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

            bind_result = None
            if 'moduleBinding' in config:
                val = config['moduleBinding']
                old_binding = getattr(polyTypedObj, 'moduleBinding', None)
                # Allow null/empty to unbind
                polyTypedObj.moduleBinding = val if val else None
                # Update the module_classes tracking on the server
                if hasattr(self.polServer, '_module_classes'):
                    # Remove from old module
                    for mid, classes in self.polServer._module_classes.items():
                        if className in classes:
                            classes.remove(className)
                    # Add to new module
                    if val:
                        if val not in self.polServer._module_classes:
                            self.polServer._module_classes[val] = []
                        if className not in self.polServer._module_classes[val]:
                            self.polServer._module_classes[val].append(className)

                # Write class source file to the module if requested
                write_to_module = config.get('writeToModule', False)
                if val and write_to_module:
                    try:
                        from moduleService.moduleScaffoldGenerator import bind_class_to_module
                        bind_result = bind_class_to_module(className, polyTypedObj, val)
                    except Exception as we:
                        print(f"[UpdateClassConfig] Warning: Failed to write class to module: {we}")
                        import traceback
                        traceback.print_exc()
                        bind_result = {'error': str(we)}

            # Build response config from current state
            response_config = {
                'isStateSpaceObject': getattr(polyTypedObj, 'isStateSpaceObject', False),
                'allowClassEdit': getattr(polyTypedObj, 'allowClassEdit', False),
                'excludeFromCRUDE': getattr(polyTypedObj, 'excludeFromCRUDE', False),
                'moduleBinding': getattr(polyTypedObj, 'moduleBinding', None),
            }

            resp = {
                'success': True,
                'className': className,
                'config': response_config,
            }
            if bind_result:
                resp['moduleWriteResult'] = bind_result

            response.status = falcon.HTTP_200
            response.media = resp

        except json.JSONDecodeError:
            response.status = falcon.HTTP_400
            response.media = {'success': False, 'error': 'Invalid JSON in request body'}
        except Exception as e:
            response.status = falcon.HTTP_500
            response.media = {'success': False, 'error': str(e)}

        response.set_header('Powered-By', 'Polari')

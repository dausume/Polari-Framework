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


from objectTreeDecorators import *
import falcon

# Custom API endpoint for managerObject - returns metadata about the manager
# without exposing the entire object tree
class managerObjectAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/managerObject'
        if polServer != None:
            polServer.falconServer.add_route(self.apiName, self)

    # Read endpoint - returns manager metadata
    def on_get(self, request, response):
        try:
            # Return only immediate metadata about the manager, not full object tree
            managerInfo = {
                "manager": {
                    "id": getattr(self.manager, 'id', 'manager'),
                    "hasServer": getattr(self.manager, 'hasServer', False),
                    "hasDB": getattr(self.manager, 'hasDB', False),
                    "complete": getattr(self.manager, 'complete', False),
                    # List of available object types
                    "availableObjectTypes": list(self.manager.objectTypingDict.keys()) if hasattr(self.manager, 'objectTypingDict') else [],
                    # Count of instances per type
                    "instanceCounts": {k: len(v) for k, v in self.manager.objectTables.items()} if hasattr(self.manager, 'objectTables') else {}
                }
            }

            # Match the standard CRUDE response format: [{ "className": { instances } }]
            jsonObj = {"managerObject": managerInfo}
            response.media = [jsonObj]
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            print(f"[managerObjectAPI] Error in GET: {err}")

        response.set_header('Powered-By', 'Polari')

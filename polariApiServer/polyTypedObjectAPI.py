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

# Custom API endpoint for polyTypedObject - returns typing information
# for database automation and data flow analysis
class polyTypedObjectAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/typing-analysis'
        if polServer != None:
            polServer.falconServer.add_route(self.apiName, self)

    # Read endpoint - returns all polyTypedObject instances with their typing data
    def on_get(self, request, response):
        try:
            # Get all polyTypedObject instances from the manager
            typingData = {}

            if hasattr(self.manager, 'objectTypingDict'):
                for className, typingObj in self.manager.objectTypingDict.items():
                    # Extract relevant typing information for each class
                    varData = []
                    if hasattr(typingObj, 'polyTypedVars'):
                        for var in typingObj.polyTypedVars:
                            varInfo = {
                                "name": getattr(var, 'name', 'unknown'),
                                "pythonTypeDefault": getattr(var, 'pythonTypeDefault', 'str'),
                                "displayName": getattr(var, 'displayName', getattr(var, 'name', 'unknown')),
                                "recordedTypes": list(getattr(var, 'recordedTypes', set())),
                                "recordedFormats": list(getattr(var, 'recordedFormats', set())),
                                "isPrimary": getattr(var, 'isPrimary', False),
                                "isIdentifier": getattr(var, 'isIdentifier', False),
                                "isUnique": getattr(var, 'isUnique', False)
                            }
                            varData.append(varInfo)

                    typingData[className] = {
                        "className": className,
                        "identifiers": getattr(typingObj, 'identifiers', []),
                        "requiredParams": getattr(typingObj, 'kwRequiredParams', []),
                        "defaultParams": getattr(typingObj, 'kwDefaultParams', []),
                        "variables": varData,
                        "dataOccupation": {
                            "json": getattr(typingObj, 'perInstanceDataCostDictJSON', {}),
                            "python": getattr(typingObj, 'perInstanceDataCostDictPython', {}),
                            "db": getattr(typingObj, 'perInstanceDataCostDictDB', {})
                        },
                        "objectReferences": getattr(typingObj, 'objectReferencesDict', {})
                    }

            # Match the standard CRUDE response format: [{ "className": { instances } }]
            jsonObj = {"polyTypedObject": typingData}
            response.media = [jsonObj]
            response.status = falcon.HTTP_200
        except Exception as err:
            response.status = falcon.HTTP_500
            print(f"[polyTypedObjectAPI] Error in GET: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

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

# Custom API endpoint that returns instance counts for all classes
# Used by frontend to determine which classes have instances (active) vs no instances (unused)
class classInstanceCountsAPI(treeObject):
    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/classInstanceCounts'
        if polServer != None:
            polServer.falconServer.add_route(self.apiName, self)

    # Read endpoint - returns instance counts for all classes
    def on_get(self, request, response):
        try:
            # Get all object types from the manager
            all_types = list(self.manager.objectTypingDict.keys()) if hasattr(self.manager, 'objectTypingDict') else []

            # Build instance count data
            instance_counts = {}
            classes_with_instances = []
            classes_without_instances = []

            for className in all_types:
                # Get instance count from objectTables
                count = len(self.manager.objectTables.get(className, {})) if hasattr(self.manager, 'objectTables') else 0
                instance_counts[className] = count

                if count > 0:
                    classes_with_instances.append(className)
                else:
                    classes_without_instances.append(className)

            # Sort lists alphabetically
            classes_with_instances.sort()
            classes_without_instances.sort()

            result_data = {
                "totalClasses": len(all_types),
                "classesWithInstances": classes_with_instances,
                "classesWithoutInstances": classes_without_instances,
                "instanceCounts": instance_counts
            }

            # Match the standard response format
            jsonObj = {"classInstanceCounts": result_data}
            response.media = [jsonObj]
            response.status = falcon.HTTP_200

        except Exception as err:
            response.status = falcon.HTTP_500
            print(f"[classInstanceCountsAPI] Error in GET: {err}")

        response.set_header('Powered-By', 'Polari')

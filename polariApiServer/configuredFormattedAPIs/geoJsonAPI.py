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
GeoJSON API Endpoint

Serves object instances as GeoJSON FeatureCollections by pulling data
from the SQLite database and using GeoJsonDefinition configs to extract
coordinates and build proper GeoJSON Point features.

    GET /geojson/{ClassName} returns:
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {
            "type": "Point",
            "coordinates": [-98.5795, 39.8283]
          },
          "properties": {"id": "abc", "name": "foo", ...}
        }
      ]
    }

These endpoints are NOT created by default -- they are only registered
when a user enables the GeoJSON format for a specific object type
via the API Config page.
"""

from objectTreeDecorators import treeObject, treeObjectInit
import falcon
import json


class GeoJsonAPI(treeObject):
    """
    API endpoint providing GeoJSON FeatureCollections from the database.

    Uses GeoJsonDefinition configs to determine how to extract coordinates
    from object instances. Registered dynamically when the GeoJSON format
    is enabled for an object type. Route is customizable (default prefix: /geojson/).
    """

    @treeObjectInit
    def __init__(self, apiObject, polServer, manager=None):
        self.polServer = polServer
        self.apiObject = apiObject
        self.objTyping = self.manager.objectTypingDict[self.apiObject]
        # Build endpoint from the ApiFormatConfig prefix
        formatConfig = self.objTyping.apiFormatConfig
        self.apiName = formatConfig.buildEndpoint(formatConfig.geoJsonPrefix)
        if polServer is not None:
            polServer.falconServer.add_route(self.apiName, self)

    def _findDatabaseForClass(self):
        """Find a managedDatabase instance that has a table for this class.
        If the DB exists but no table for this class, create it on-demand."""
        db = getattr(self.manager, 'db', None)
        if db is None:
            return None
        # Check if table exists
        if hasattr(db, 'tables') and self.apiObject in db.tables:
            return db
        # Table doesn't exist yet — try to create it on-demand
        if self.apiObject in self.manager.objectTypingDict:
            polyTypedObj = self.manager.objectTypingDict[self.apiObject]
            try:
                if polyTypedObj.polyTypedVarsDict:
                    polyTypedObj.makeTypedTableFromAnalysis()
                elif polyTypedObj.polariSourceFile is not None:
                    polyTypedObj.makeGeneralizedTable()
                # Check again after creation
                if self.apiObject in db.tables:
                    return db
            except Exception as e:
                print(f'[GeoJsonAPI] Could not create table for {self.apiObject}: {e}')
        return None

    def _getPermissions(self, userAuthInfo):
        """Reuse permission check from the CRUDE endpoint for Read access."""
        if hasattr(self.polServer, 'crudeObjectsList'):
            for crudeObj in self.polServer.crudeObjectsList:
                if getattr(crudeObj, 'apiObject', None) == self.apiObject:
                    return crudeObj.getUsersObjectAccessPermissions(userAuthInfo)
        # Fallback: check base access dictionary on the typing object
        baseAccess = getattr(self.objTyping, 'baseAccessDictionary', {})
        if 'R' in baseAccess:
            return baseAccess, baseAccess
        return {}, {}

    def _findGeoJsonDefinition(self):
        """Find the GeoJsonDefinition config for this class's source_class."""
        if 'GeoJsonDefinition' not in self.manager.objectTables:
            return None
        for defId, defInstance in self.manager.objectTables['GeoJsonDefinition'].items():
            if getattr(defInstance, 'source_class', '') == self.apiObject:
                return defInstance
        return None

    def _parseCoordinates(self, instance, coordConfig):
        """Extract lat/lng from an instance based on coordinate configuration.

        Returns (lng, lat) tuple or (None, None) if coordinates can't be extracted.
        GeoJSON uses [lng, lat] order per RFC 7946.
        """
        coordinateMode = coordConfig.get('coordinateMode', 'separate')
        lng = None
        lat = None

        if coordinateMode == 'tuple':
            tupleVariable = coordConfig.get('tupleVariable', '')
            tupleOrder = coordConfig.get('tupleOrder', 'lat-lng')
            if tupleVariable and tupleVariable in instance:
                tupleVal = instance[tupleVariable]
                # Parse tuple value - could be a string representation or actual list
                if isinstance(tupleVal, str):
                    try:
                        tupleVal = json.loads(tupleVal)
                    except (json.JSONDecodeError, ValueError):
                        return None, None
                if isinstance(tupleVal, (list, tuple)) and len(tupleVal) >= 2:
                    try:
                        if tupleOrder == 'lat-lng':
                            lat = float(tupleVal[0])
                            lng = float(tupleVal[1])
                        else:  # lng-lat
                            lng = float(tupleVal[0])
                            lat = float(tupleVal[1])
                    except (ValueError, TypeError):
                        return None, None

        elif coordinateMode == 'separate':
            latVar = coordConfig.get('latitudeVariable', '')
            lngVar = coordConfig.get('longitudeVariable', '')
            if latVar and latVar in instance:
                try:
                    lat = float(instance[latVar])
                except (ValueError, TypeError):
                    pass
            if lngVar and lngVar in instance:
                try:
                    lng = float(instance[lngVar])
                except (ValueError, TypeError):
                    pass

        # 'parent' mode returns no coordinates (handled by parent class)

        return lng, lat

    def on_get(self, request, response):
        """Read all instances from DB and return as GeoJSON FeatureCollection."""
        # Check if format is still enabled
        formatConfig = self.objTyping.apiFormatConfig
        if formatConfig is None or not formatConfig.geoJsonEnabled:
            response.status = falcon.HTTP_404
            response.media = {"error": f"GeoJSON API not enabled for {self.apiObject}"}
            return

        # Permission check
        userAuthInfo = request.auth
        (accessQueryDict, permissionQueryDict) = self._getPermissions(userAuthInfo)
        if 'R' not in accessQueryDict:
            response.status = falcon.HTTP_405
            response.media = {"error": "Read access not allowed for this user on this object type."}
            return

        try:
            db = self._findDatabaseForClass()
            if db is None:
                response.status = falcon.HTTP_503
                response.media = {
                    "error": f"No database table found for '{self.apiObject}'. "
                             f"A database with a table for this class must be set up before "
                             f"the GeoJSON API can serve data."
                }
                return

            # Find GeoJsonDefinition for this class
            geoDef = self._findGeoJsonDefinition()
            if geoDef is None:
                response.status = falcon.HTTP_404
                response.media = {
                    "error": f"No GeoJsonDefinition found for '{self.apiObject}'. "
                             f"Create a GeoJSON configuration for this class first."
                }
                return

            # Parse the GeoJsonDefinition's definition JSON
            definitionStr = getattr(geoDef, 'definition', '{}')
            try:
                definitionData = json.loads(definitionStr) if isinstance(definitionStr, str) else definitionStr
            except (json.JSONDecodeError, ValueError):
                definitionData = {}

            # Extract coordinate config from the geoJsonConfig sub-object
            coordConfig = definitionData.get('geoJsonConfig', definitionData)

            # Query database directly
            (columnNames, dataTuples) = db.getAllInTable(self.apiObject)

            # Build GeoJSON FeatureCollection
            features = []
            for row in dataTuples:
                # Build instance dict from row
                instance = {}
                for i, colName in enumerate(columnNames):
                    instance[colName] = row[i]

                # Extract coordinates
                lng, lat = self._parseCoordinates(instance, coordConfig)

                if lng is not None and lat is not None:
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lng, lat]
                        },
                        "properties": instance
                    }
                    features.append(feature)

            result = {
                "type": "FeatureCollection",
                "features": features
            }

            response.media = result
            response.status = falcon.HTTP_200

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"error": str(err)}
            print(f"[GeoJsonAPI] Error querying {self.apiObject}: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

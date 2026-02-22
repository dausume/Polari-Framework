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
D3 Column-Oriented API Endpoint

Provides column-oriented (data-series style) JSON by pulling data directly
from the SQLite database instead of the in-memory object tree. This format
is optimized for d3.js graphing libraries and other column-oriented consumers.

Unlike CRUDE endpoints which return the complex nested Polari tree format,
this endpoint returns data organized by columns:

    GET /d3/{ClassName} returns:
    {
      "columns": ["id", "name", "value"],
      "data": {
        "id": ["abc", "def"],
        "name": ["foo", "bar"],
        "value": [42, 99]
      },
      "length": 2
    }

These endpoints are NOT created by default -- they are only registered
when a user enables the D3 Column format for a specific object type
via the API Config page.
"""

from objectTreeDecorators import treeObject, treeObjectInit
import falcon


class D3ColumnAPI(treeObject):
    """
    API endpoint providing column-oriented (D3-style) JSON from the database.

    Registered dynamically when the D3 Column format is enabled for an
    object type. Route is customizable (default prefix: /d3/).
    """

    @treeObjectInit
    def __init__(self, apiObject, polServer, manager=None):
        self.polServer = polServer
        self.apiObject = apiObject
        self.objTyping = self.manager.objectTypingDict[self.apiObject]
        # Build endpoint from the ApiFormatConfig prefix
        formatConfig = self.objTyping.apiFormatConfig
        self.apiName = formatConfig.buildEndpoint(formatConfig.d3ColumnPrefix)
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
                print(f'[D3ColumnAPI] Could not create table for {self.apiObject}: {e}')
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

    def on_get(self, request, response):
        """Read all instances from DB as column-oriented JSON."""
        # Check if format is still enabled
        formatConfig = self.objTyping.apiFormatConfig
        if formatConfig is None or not formatConfig.d3ColumnEnabled:
            response.status = falcon.HTTP_404
            response.media = {"error": f"D3 Column API not enabled for {self.apiObject}"}
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
                             f"the D3 Column API can serve data."
                }
                return

            # Query database directly
            (columnNames, dataTuples) = db.getAllInTable(self.apiObject)

            # Build column-oriented structure
            columnData = {}
            for colName in columnNames:
                columnData[colName] = []

            for row in dataTuples:
                for i, colName in enumerate(columnNames):
                    columnData[colName].append(row[i])

            result = {
                "columns": list(columnNames),
                "data": columnData,
                "length": len(dataTuples)
            }

            response.media = result
            response.status = falcon.HTTP_200

        except Exception as err:
            response.status = falcon.HTTP_500
            response.media = {"error": str(err)}
            print(f"[D3ColumnAPI] Error querying {self.apiObject}: {err}")
            import traceback
            traceback.print_exc()

        response.set_header('Powered-By', 'Polari')

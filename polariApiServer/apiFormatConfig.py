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
API Format Configuration Sub-Object

A one-to-one configuration sub-object on polyTypedObject that manages
which API formats are enabled for a given object type, along with their
customizable endpoint prefixes.

Three format types:
- Polari Tree (CRUDE): Always enabled, pulls from in-memory object tree.
  Complex nested format ideal for inter-polari communication.
- Flat JSON: Opt-in, pulls from database. Traditional single-object
  single-level REST JSON.
- D3 Column Series: Opt-in, pulls from database. Column-oriented JSON
  for d3 graphing libraries.

The Flat JSON and D3 Column formats are NOT created by default. They
represent the 'Real World API' structure for after the tree is collapsed.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ApiFormatConfig(treeObject):
    """
    Configuration sub-object managing API format endpoints for a polyTypedObject.

    Each polyTypedObject has exactly one ApiFormatConfig instance.
    The tree handles the parent-child relationship automatically.
    """

    @treeObjectInit
    def __init__(self, polyTypedObj=None, manager=None):
        self.polyTypedObj = polyTypedObj
        self.manager = polyTypedObj.manager if polyTypedObj else manager
        self.className = polyTypedObj.className if polyTypedObj else None

        # Polari Tree format (always available, endpoint is the CRUDE endpoint)
        self.polariTreeEnabled = True
        self.polariTreeEndpoint = None  # Set when CRUDE is registered: '/{ClassName}'

        # Flat JSON format (opt-in, DB-backed)
        self.flatJsonEnabled = False
        self.flatJsonEndpoint = None     # Active endpoint path when enabled
        self.flatJsonPrefix = '/flat/'   # Customizable prefix

        # D3 Column Series format (opt-in, DB-backed)
        self.d3ColumnEnabled = False
        self.d3ColumnEndpoint = None     # Active endpoint path when enabled
        self.d3ColumnPrefix = '/d3/'     # Customizable prefix

    def buildEndpoint(self, prefix):
        """Build a full endpoint path from prefix + className."""
        if not prefix.startswith('/'):
            prefix = '/' + prefix
        if not prefix.endswith('/'):
            prefix = prefix + '/'
        return prefix + self.className

    def getEndpointForFormat(self, formatType):
        """Get the full endpoint path for a given format type."""
        if formatType == 'polariTree':
            return self.polariTreeEndpoint
        elif formatType == 'flatJson':
            return self.flatJsonEndpoint
        elif formatType == 'd3Column':
            return self.d3ColumnEndpoint
        return None

    def getPrefixForFormat(self, formatType):
        """Get the customizable prefix for a given format type."""
        if formatType == 'flatJson':
            return self.flatJsonPrefix
        elif formatType == 'd3Column':
            return self.d3ColumnPrefix
        return None

    def isFormatEnabled(self, formatType):
        """Check if a given format type is enabled."""
        if formatType == 'polariTree':
            return self.polariTreeEnabled
        elif formatType == 'flatJson':
            return self.flatJsonEnabled
        elif formatType == 'd3Column':
            return self.d3ColumnEnabled
        return False

    def getAllActiveEndpoints(self):
        """Return a list of all currently active endpoint paths."""
        endpoints = []
        if self.polariTreeEndpoint:
            endpoints.append(self.polariTreeEndpoint)
        if self.flatJsonEnabled and self.flatJsonEndpoint:
            endpoints.append(self.flatJsonEndpoint)
        if self.d3ColumnEnabled and self.d3ColumnEndpoint:
            endpoints.append(self.d3ColumnEndpoint)
        return endpoints

    def toDict(self):
        """Serialize to dict for API response."""
        return {
            "polariTree": {
                "enabled": self.polariTreeEnabled,
                "endpoint": self.polariTreeEndpoint,
                "prefix": None,
                "description": "Complex nested tree format (inter-polari communication)"
            },
            "flatJson": {
                "enabled": self.flatJsonEnabled,
                "endpoint": self.flatJsonEndpoint,
                "prefix": self.flatJsonPrefix,
                "description": "Traditional flat JSON (standard REST)"
            },
            "d3Column": {
                "enabled": self.d3ColumnEnabled,
                "endpoint": self.d3ColumnEndpoint,
                "prefix": self.d3ColumnPrefix,
                "description": "Column-oriented series JSON (d3 graphing)"
            }
        }

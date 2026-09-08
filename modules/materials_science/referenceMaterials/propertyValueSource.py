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
PropertyValueSource Model

Represents a cited property value from a specific source.
Allows tracking multiple measurements/values for the same property
from different sources. Source citation details are now delegated
to the DataProvenance system via provenanceId.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PropertyValueSource(treeObject):
    """
    A cited property value linked to provenance metadata.

    Links a property measurement to its source documentation via
    the DataProvenance system, enabling verification and comparison
    across sources.

    Attributes:
        referenceMaterialId: ID of the reference material this value belongs to
        propertyName: Name of the property (e.g., 'MeltingPoint', 'Viscosity')
        propertyClass: Class name of the property for linking

        # Value data
        value: The measured/reported value
        valueMin: Minimum value if a range
        valueMax: Maximum value if a range
        unit: Unit of measurement
        testConditions: Conditions under which value was measured

        # Quality indicators
        sampleSize: Number of samples if known
        standardUsed: Testing standard used (e.g., ASTM D638)

        # Provenance
        provenanceId: ID of the DataProvenance record for source citation
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 referenceMaterialId='',
                 propertyName='',
                 propertyClass='',
                 # Value data
                 value=0.0,
                 valueMin=0.0,
                 valueMax=0.0,
                 unit='',
                 testConditions='',
                 # Quality indicators
                 sampleSize=0,
                 standardUsed='',
                 # Provenance
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.referenceMaterialId = referenceMaterialId
        self.propertyName = propertyName
        self.propertyClass = propertyClass

        # Value data
        self.value = value
        self.valueMin = valueMin
        self.valueMax = valueMax
        self.unit = unit
        self.testConditions = testConditions

        # Quality indicators
        self.sampleSize = sampleSize
        self.standardUsed = standardUsed

        # Provenance
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"PropertyValueSource(id='{self.id}', material='{self.referenceMaterialId}', property='{self.propertyName}', value={self.value})"

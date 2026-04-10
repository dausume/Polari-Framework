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
ReferenceMaterial Model

Base class for well-known reference materials with documented property values
from various sources. These serve as baselines for comparison and validation.

Reference materials have:
- Known/documented property values
- Citations to sources (academic, manufacturer, community)
- Multiple measurements from different sources for the same property
"""

from objectTreeDecorators import treeObject, treeObjectInit


class ReferenceMaterial(treeObject):
    """
    Base class for reference materials with documented properties.

    Reference materials are well-characterized materials with known
    property values from literature, manufacturer data sheets, or
    community-sourced measurements.

    Attributes:
        name: Common name of the material (e.g., 'PLA', 'ABS')
        fullName: Full chemical/technical name
        description: Description of the material
        category: Material category (thermoplastic, thermoset, composite, etc.)
        chemicalFormula: Chemical formula if applicable
        casNumber: CAS registry number if applicable

        # Classification
        materialFamily: Broader family (polyester, polyamide, etc.)
        polymerType: Type of polymer (thermoplastic, thermoset, elastomer)

        # General characteristics
        biodegradable: Whether the material is biodegradable
        foodSafe: Whether the material is food-safe (general)
        uvResistant: General UV resistance
        chemicalResistance: General chemical resistance description

        # Reference data
        sourceCount: Number of sources with data for this material
        notes: Additional notes about this reference material

    Class Constants:
        MATERIAL_TYPE: Identifier for the material type
    """

    MATERIAL_TYPE = 'reference'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 fullName='',
                 description='',
                 category='thermoplastic',
                 chemicalFormula='',
                 casNumber='',
                 # Classification
                 materialFamily='',
                 polymerType='thermoplastic',
                 # General characteristics
                 biodegradable=False,
                 foodSafe=False,
                 uvResistant=False,
                 chemicalResistance='',
                 # Reference data
                 sourceCount=0,
                 notes=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.fullName = fullName
        self.description = description
        self.category = category
        self.chemicalFormula = chemicalFormula
        self.casNumber = casNumber

        # Classification
        self.materialFamily = materialFamily
        self.polymerType = polymerType

        # General characteristics
        self.biodegradable = biodegradable
        self.foodSafe = foodSafe
        self.uvResistant = uvResistant
        self.chemicalResistance = chemicalResistance

        # Reference data
        self.sourceCount = sourceCount
        self.notes = notes

    def __repr__(self):
        return f"ReferenceMaterial(id='{self.id}', name='{self.name}')"

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
Material Model

The foundational base class representing an actual material.
Materials are real-world substances (e.g., "Epoxy Resin", "Polyethylene", "Steel")
that can have properties and resolution-level definitions attached to them.

A Material serves as the anchor point for:
- MaterialProperty: Measurable properties (viscosity, hardness, melting point, etc.)
- MaterialResolution: Multi-scale simulation definitions (experimental, FEM, CGMD, MD, DFT)

Example:
    material = Material(name="Epoxy Resin 2000", description="Two-part epoxy adhesive")

    # Attach properties
    viscosity = KrebsViscosity(materialId=material.id, viscosityKU=85.0)
    hardness = ShoreMeasurement(materialId=material.id, hardnessReading=75, shoreType='D')

    # Attach resolution definitions
    experimental = RawExperimentalMaterial(materialId=material.id, ...)
    fem_material = ConsistentFiniteElementMaterial(materialId=material.id, ...)
"""

from objectTreeDecorators import treeObject, treeObjectInit


class Material(treeObject):
    """
    Base class representing an actual material.

    This is the foundational object that represents a real-world material.
    Properties and resolution-level definitions are attached to materials
    via their materialId reference.

    Attributes:
        name: Name of the material (e.g., "Epoxy Resin 2000")
        description: Description of the material
        category: Material category (polymer, metal, ceramic, composite, etc.)
        manufacturer: Manufacturer or source of the material
        tradeName: Commercial trade name if applicable
        cas: CAS registry number if applicable
        notes: Additional notes about the material
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='',
                 description='',
                 category='',
                 manufacturer='',
                 tradeName='',
                 cas='',
                 notes=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.name = name
        self.description = description
        self.category = category
        self.manufacturer = manufacturer
        self.tradeName = tradeName
        self.cas = cas
        self.notes = notes

    def __repr__(self):
        return f"Material(id='{self.id}', name='{self.name}')"

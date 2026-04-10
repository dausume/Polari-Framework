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
PropertyCategory Model

Base class for material property categories. Categories group related
properties that share common physical principles or measurement domains.

Categories:
- RheologicalProperty: Flow and deformation (viscosity, elasticity, MFI)
- MechanicalProperty: Strength and resistance (hardness, tensile strength)
- SurfaceProperty: Interfacial phenomena (surface energy, surface tension)
- ThermalProperty: Temperature-dependent (melting point, Tg, CTE)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.materialProperty import MaterialProperty


class PropertyCategory(MaterialProperty):
    """
    Base class for material property categories.

    Categories serve as organizational groupings for related material properties.
    Each category represents a domain of physical behavior (rheological,
    mechanical, surface, thermal, etc.).

    Attributes:
        materialId: ID reference to the parent Material
        categoryDescription: Description of what properties this category encompasses
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Property Category',
                 description='Base category for material properties',
                 materialId='',
                 categoryDescription=''):
        MaterialProperty.__init__(self, manager=manager, branch=branch, id=id,
                                  name=name, description=description)
        self.materialId = materialId
        self.categoryDescription = categoryDescription

    def __repr__(self):
        return f"PropertyCategory(id='{self.id}', name='{self.name}')"

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
MechanicalProperty Model

Mechanical properties relate to the strength and resistance of materials
under applied forces. This serves as a category beneath PropertyCategory
for properties like:
- Hardness (resistance to localized deformation)
- Tensile Strength (resistance to being pulled apart)
- Compressive Strength (resistance to compression)
- Flexural Strength (resistance to bending)
- Impact Resistance (resistance to sudden force)

Mechanical properties are critical for:
- Structural materials
- Protective coatings
- Polymers and composites
- Metals and ceramics
- 3D printed parts

Standards References:
- ASTM E384: Microindentation hardness of materials
- ASTM D2240: Rubber property - Durometer hardness
- ASTM D638: Tensile properties of plastics
- ISO 527: Plastics - Determination of tensile properties
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.propertyCategory import PropertyCategory


class MechanicalProperty(PropertyCategory):
    """
    Mechanical property category inheriting from PropertyCategory.

    Mechanical properties describe how materials respond to applied forces,
    including their strength, hardness, and deformation characteristics.

    Child Properties:
    - hardness/: Hardness → HardnessScale → Shore/Rockwell/Vickers measurements
    - tensileStrength/: TensileStrength → UltimateTensileStrength → TensileMeasurement

    Attributes:
        materialId: ID reference to the parent Material
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Mechanical Property',
                 description='Property relating to strength and resistance under applied forces',
                 materialId='',
                 categoryDescription='Strength and resistance properties including hardness and tensile strength'):
        PropertyCategory.__init__(self, manager=manager, branch=branch, id=id,
                                  name=name, description=description,
                                  materialId=materialId, categoryDescription=categoryDescription)

    def __repr__(self):
        return f"MechanicalProperty(id='{self.id}', name='{self.name}', materialId='{self.materialId}')"

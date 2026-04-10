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
SpecificGravity Model

Abstract specific gravity property that inherits from MaterialProperty.
This serves as the intermediate abstraction between the core MaterialProperty
and specific gravity measurement types.

Specific gravity is the ratio of the density of a substance to the density
of a reference substance (typically water at 4°C for liquids/solids, or air for gases).

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
- Level 1: SpecificGravity (this class - abstract specific gravity concept)
- Level 2: ReferentialSpecificGravity (normalized against reference material)
- Level 3: Raw measurements (Pycnometer, Hydrometer, DensityMeter, etc.)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.materialProperty import MaterialProperty


class SpecificGravity(MaterialProperty):
    """
    Abstract specific gravity property inheriting from MaterialProperty.

    This represents the concept of specific gravity as a material property,
    serving as the parent abstraction for specific gravity types like
    ReferentialSpecificGravity (derived values) and raw measurement types.

    Abstraction level: 1 (MaterialProperty is 0)

    Attributes:
        materialId: ID reference to the parent Material
        abstractionLevel: Numeric level indicating specificity (1 for this class)
    """

    ABSTRACTION_LEVEL = 1

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Specific Gravity',
                 description='Ratio of substance density to reference substance density',
                 materialId=''):
        MaterialProperty.__init__(self, manager=manager, branch=branch, id=id,
                                  name=name, description=description)
        self.materialId = materialId
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"SpecificGravity(id='{self.id}', materialId='{self.materialId}')"

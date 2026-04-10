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
Hardness Model

Represents the abstract concept of hardness - a material's resistance
to localized plastic deformation. Inherits from MechanicalProperty at
abstraction level 1.

Hardness measurement types:
- Shore Hardness: Elastomers and soft plastics (durometer)
- Rockwell Hardness: Metals and hard plastics (depth under load)
- Vickers Hardness: All materials (diamond pyramid indentation)
- Brinell Hardness: Metals (steel ball indentation)
- Mohs Hardness: Minerals (scratch resistance scale 1-10)
- Pencil Hardness: Coatings (scratch by pencil leads)

Standards References:
- ASTM D2240: Rubber property - Durometer hardness (Shore)
- ASTM E18: Rockwell hardness of metallic materials
- ASTM E384: Microindentation hardness of materials (Vickers)
- ASTM E10: Brinell hardness of metallic materials
- ASTM D3363: Film hardness by pencil test

Open Source References:
- OpenHardness: DIY durometer designs using force sensors
- Arduino hardness testers: Load cell + displacement measurement
- 3D printed durometer: RepRap community designs
- Pencil hardness: Most accessible DIY method (no special equipment)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - MechanicalProperty (strength/resistance category)
    - Level 1: Hardness (this class - abstract concept)
    - Level 2: HardnessScale (derived/standard value)
    - Level 3: ShoreMeasurement, RockwellMeasurement, VickersMeasurement
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.mechanical.mechanicalProperty import MechanicalProperty


class Hardness(MechanicalProperty):
    """
    Abstract hardness property (Level 1).

    Represents the concept of hardness - resistance to localized
    deformation by indentation or scratching. This is the abstract
    parent for specific hardness scales and measurements.

    Abstraction level: 1 (abstract concept)

    Attributes:
        materialId: ID reference to the parent Material
    """

    ABSTRACTION_LEVEL = 1

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Hardness',
                 description='Material resistance to localized plastic deformation',
                 materialId=''):
        MechanicalProperty.__init__(self, manager=manager, branch=branch, id=id,
                                    name=name, description=description,
                                    materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"Hardness(id='{self.id}', materialId='{self.materialId}')"

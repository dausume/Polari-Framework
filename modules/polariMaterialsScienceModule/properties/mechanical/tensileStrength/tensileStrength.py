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
TensileStrength Model

Represents the abstract concept of tensile strength - the maximum stress
a material can withstand while being stretched or pulled before breaking.
Inherits from MechanicalProperty at abstraction level 1.

Tensile properties include:
- Ultimate Tensile Strength (UTS): Maximum stress before failure
- Yield Strength: Stress at onset of plastic deformation
- Elongation at Break: Strain percentage at fracture
- Young's Modulus: Stiffness (stress/strain in elastic region)
- Toughness: Energy absorbed before fracture (area under curve)

Applications:
- Structural material selection
- 3D printing filament characterization
- Fiber and textile evaluation
- Adhesive and sealant testing
- Quality control in manufacturing

Standards References:
- ASTM D638: Tensile properties of plastics
- ASTM D882: Tensile properties of thin plastic sheeting
- ASTM E8/E8M: Tension testing of metallic materials
- ISO 527: Plastics - Determination of tensile properties
- ISO 6892-1: Metallic materials - Tensile testing

Open Source References:
- OpenTensile: DIY tensile testers using stepper motors and load cells
- Universal Testing Machine (UTM) DIY: Arduino-based designs
- RepRap community: Tensile testers for 3D printing filament QC
- OpenQCM: Quartz crystal microbalance with tensile capabilities

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - MechanicalProperty (strength/resistance category)
    - Level 1: TensileStrength (this class - abstract concept)
    - Level 2: UltimateTensileStrength (derived/standard value)
    - Level 3: TensileMeasurement (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.mechanical.mechanicalProperty import MechanicalProperty


class TensileStrength(MechanicalProperty):
    """
    Abstract tensile strength property (Level 1).

    Represents the concept of tensile strength - material resistance
    to being pulled apart. This is the abstract parent for specific
    tensile values and measurements.

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
                 name='Tensile Strength',
                 description='Maximum stress material can withstand while being stretched',
                 materialId=''):
        MechanicalProperty.__init__(self, manager=manager, branch=branch, id=id,
                                    name=name, description=description,
                                    materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"TensileStrength(id='{self.id}', materialId='{self.materialId}')"

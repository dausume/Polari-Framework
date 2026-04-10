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
LiquidSurfaceTension Model

Represents the abstract concept of liquid surface tension - the cohesive
force at the liquid-air interface that causes liquids to minimize surface
area. Inherits from SurfaceProperty at abstraction level 1.

Surface tension (γ) is defined as force per unit length (mN/m) or
equivalently energy per unit area (mJ/m²).

Surface tension affects:
- Droplet formation and size
- Wetting and spreading behavior
- Capillary rise in tubes
- Foam stability
- Emulsion formation
- Printing and coating quality

Measurement methods:
- Wilhelmy plate: Force on partially immersed plate
- Du Noüy ring: Force to detach ring from surface
- Pendant drop: Shape analysis of hanging drop
- Spinning drop: For very low interfacial tensions
- Capillary rise: Height in narrow tube

Standards References:
- ASTM D1331: Surface and interfacial tension of solutions
- ASTM D971: Interfacial tension by ring method
- ISO 304: Surface active agents - Determination of surface tension
- ISO 6295: Petroleum products - Interfacial tension

Open Source References:
- OpenDrop: Pendant drop analysis software (github.com/opendrop)
- PyDrop: Python pendant drop analysis
- DIY tensiometers: Force sensor + plate/ring designs
- Arduino-based Wilhelmy plate systems

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - SurfaceProperty (interfacial phenomena category)
    - Level 1: LiquidSurfaceTension (this class - abstract concept)
    - Level 2: SurfaceTensionValue (derived/standard value)
    - Level 3: WilhelmyMeasurement, DuNouyMeasurement, PendantDropMeasurement
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.surface.surfaceProperty import SurfaceProperty


class LiquidSurfaceTension(SurfaceProperty):
    """
    Abstract liquid surface tension property (Level 1).

    Represents the concept of liquid surface tension - the cohesive
    force at the liquid-air interface.

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
                 name='Liquid Surface Tension',
                 description='Cohesive force at liquid-air interface',
                 materialId=''):
        SurfaceProperty.__init__(self, manager=manager, branch=branch, id=id,
                                 name=name, description=description,
                                 materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"LiquidSurfaceTension(id='{self.id}', materialId='{self.materialId}')"

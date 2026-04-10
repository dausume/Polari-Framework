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
GlassTransition Model

Represents the abstract concept of glass transition temperature (Tg) -
the temperature region where amorphous materials transition from a hard,
glassy state to a soft, rubbery state. Inherits from ThermalProperty at
abstraction level 1.

Glass transition characteristics:
- Second-order transition (no latent heat)
- Continuous change in properties (not a sharp transition)
- Affects modulus, specific heat, expansion coefficient
- Dependent on cooling/heating rate
- Not a true phase transition (kinetic phenomenon)

Factors affecting Tg:
- Molecular weight (higher MW → higher Tg)
- Plasticizers (lower Tg)
- Crosslinking (higher Tg)
- Crystallinity (Tg less pronounced)
- Moisture content (water as plasticizer)

Measurement methods:
- DSC: Change in heat capacity (step)
- DMA: Peak in tan(δ) or drop in E'
- TMA: Change in expansion coefficient
- Dilatometry: Volume change

Standards References:
- ASTM E1356: Glass transition temperatures by DSC
- ASTM D7028: Glass transition by DMA
- ISO 11357-2: DSC - Determination of Tg
- ISO 6721-11: DMA - Determination of Tg

Open Source References:
- DMA-based Tg measurement is most accessible for DIY
- Arduino thermal expansion measurement possible
- DSC Tg detection more challenging (small heat flow change)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: GlassTransition (this class - abstract concept)
    - Level 2: GlassTransitionTemp (derived/standard value)
    - Level 3: DSCGlassTransitionMeasurement, DMAGlassTransitionMeasurement
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.thermalProperty import ThermalProperty


class GlassTransition(ThermalProperty):
    """
    Abstract glass transition property (Level 1).

    Represents the concept of glass transition - the reversible
    transition from glassy to rubbery state in amorphous materials.

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
                 name='Glass Transition',
                 description='Temperature of glassy to rubbery state transition',
                 materialId=''):
        ThermalProperty.__init__(self, manager=manager, branch=branch, id=id,
                                 name=name, description=description,
                                 materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"GlassTransition(id='{self.id}', materialId='{self.materialId}')"

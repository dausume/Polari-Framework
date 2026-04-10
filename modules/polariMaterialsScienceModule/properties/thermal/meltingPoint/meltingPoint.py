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
MeltingPoint Model

Represents the abstract concept of melting point - the temperature at
which a solid transforms to liquid at standard pressure. Inherits from
ThermalProperty at abstraction level 1.

Related thermal transitions:
- Melting point (Tm): Solid → Liquid (crystalline materials)
- Softening point: Gradual softening (amorphous materials)
- Pour point: Temperature where liquid stops flowing
- Freezing point: Liquid → Solid (may differ from Tm)

Measurement methods:
- DSC (Differential Scanning Calorimetry): Heat flow analysis
- DTA (Differential Thermal Analysis): Temperature difference
- Visual/capillary tube: Direct observation
- Thermomechanical Analysis (TMA): Penetration method

Applications:
- Polymer processing temperature selection
- Wax and coating formulation
- 3D printing material compatibility
- Metal casting temperature control
- Food science and cooking

Standards References:
- ASTM E794: Melting and crystallization temperatures by DSC
- ASTM D3418: Transition temperatures of polymers by DSC
- ASTM D127: Drop melting point of petroleum wax
- ISO 3146: Plastics - Determination of melting behaviour

Open Source References:
- OpenThermal: DIY thermal analysis projects
- Arduino melting point: Heated capillary tube designs
- DIY DSC: Challenging but possible with matched thermocouples

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: MeltingPoint (this class - abstract concept)
    - Level 2: MeltingPointValue (derived/standard value)
    - Level 3: DSCMeltingMeasurement, VisualMeltingMeasurement
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.thermalProperty import ThermalProperty


class MeltingPoint(ThermalProperty):
    """
    Abstract melting point property (Level 1).

    Represents the concept of melting temperature - the solid-to-liquid
    transition temperature at standard pressure.

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
                 name='Melting Point',
                 description='Temperature at which solid transforms to liquid',
                 materialId=''):
        ThermalProperty.__init__(self, manager=manager, branch=branch, id=id,
                                 name=name, description=description,
                                 materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"MeltingPoint(id='{self.id}', materialId='{self.materialId}')"

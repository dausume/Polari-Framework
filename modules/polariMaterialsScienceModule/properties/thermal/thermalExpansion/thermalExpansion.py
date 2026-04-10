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
ThermalExpansion Model

Represents the abstract concept of thermal expansion - the tendency of
materials to change dimensions with temperature. Inherits from
ThermalProperty at abstraction level 1.

Types of thermal expansion:
- Linear (CTE, α): ΔL/L₀ = α·ΔT (1D, units: 1/°C or ppm/°C)
- Volumetric (β): ΔV/V₀ = β·ΔT (3D, β ≈ 3α for isotropic materials)
- Area (surface): For thin films and coatings

Expansion behavior:
- Most materials expand when heated
- Water anomaly: Contracts from 0-4°C, then expands
- Anisotropic materials: Different CTE in different directions
- CTE often temperature-dependent

Applications:
- Thermal stress analysis
- Dimensional stability assessment
- Material compatibility (thermal mismatch)
- Precision instrument design
- 3D printing (warping prediction)

Reference CTE values (10⁻⁶/°C):
- Aluminum: 23
- Steel: 12
- Glass: 8-9
- Invar: 1.2 (low expansion alloy)
- PTFE: 100-150
- Epoxy: 50-100

Standards References:
- ASTM E831: Linear thermal expansion by TMA
- ASTM D696: Linear thermal expansion of plastics
- ASTM E228: Linear thermal expansion by push-rod dilatometer
- ISO 11359: Plastics - Thermomechanical analysis
- ISO 7991: Glass - Determination of CTE

Open Source References:
- DIY dilatometer designs using LVDT or dial gauge
- Arduino thermal expansion measurement systems
- Precision limited but useful for educational purposes

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: ThermalExpansion (this class - abstract concept)
    - Level 2: CoefficientOfThermalExpansion (derived/standard value)
    - Level 3: TMAMeasurement, DilatometerMeasurement (raw measurements)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.thermalProperty import ThermalProperty


class ThermalExpansion(ThermalProperty):
    """
    Abstract thermal expansion property (Level 1).

    Represents the concept of thermal expansion - dimensional change
    with temperature variation.

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
                 name='Thermal Expansion',
                 description='Dimensional change of material with temperature',
                 materialId=''):
        ThermalProperty.__init__(self, manager=manager, branch=branch, id=id,
                                 name=name, description=description,
                                 materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"ThermalExpansion(id='{self.id}', materialId='{self.materialId}')"

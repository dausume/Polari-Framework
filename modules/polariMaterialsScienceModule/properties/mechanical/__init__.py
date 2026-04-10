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
Mechanical Properties Module

Mechanical properties relate to strength and resistance under applied forces.

Property Modules:
- hardness/: Hardness → HardnessScale → ShoreMeasurement
- tensileStrength/: TensileStrength → UltimateTensileStrength → TensileMeasurement
"""

from polariMaterialsScienceModule.properties.mechanical.mechanicalProperty import MechanicalProperty

from polariMaterialsScienceModule.properties.mechanical.hardness import (
    Hardness, HardnessScale, ShoreMeasurement
)
from polariMaterialsScienceModule.properties.mechanical.tensileStrength import (
    TensileStrength, UltimateTensileStrength, TensileMeasurement
)

__all__ = [
    'MechanicalProperty',
    'Hardness', 'HardnessScale', 'ShoreMeasurement',
    'TensileStrength', 'UltimateTensileStrength', 'TensileMeasurement'
]

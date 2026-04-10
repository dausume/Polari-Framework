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
Thermal Properties Module

Thermal properties relate to temperature-dependent behavior of materials.

Property Modules:
- meltingPoint/: MeltingPoint → MeltingPointValue → DSCMeltingMeasurement
- glassTransition/: GlassTransition → GlassTransitionTemp → DMAGlassTransitionMeasurement
- smokingPoint/: SmokingPoint → SmokingPointValue → SmokingPointMeasurement
- thermalExpansion/: ThermalExpansion → CoefficientOfThermalExpansion → TMAMeasurement
"""

from polariMaterialsScienceModule.properties.thermal.thermalProperty import ThermalProperty

from polariMaterialsScienceModule.properties.thermal.meltingPoint import (
    MeltingPoint, MeltingPointValue, DSCMeltingMeasurement
)
from polariMaterialsScienceModule.properties.thermal.glassTransition import (
    GlassTransition, GlassTransitionTemp, DMAGlassTransitionMeasurement
)
from polariMaterialsScienceModule.properties.thermal.smokingPoint import (
    SmokingPoint, SmokingPointValue, SmokingPointMeasurement
)
from polariMaterialsScienceModule.properties.thermal.thermalExpansion import (
    ThermalExpansion, CoefficientOfThermalExpansion, TMAMeasurement
)

__all__ = [
    'ThermalProperty',
    'MeltingPoint', 'MeltingPointValue', 'DSCMeltingMeasurement',
    'GlassTransition', 'GlassTransitionTemp', 'DMAGlassTransitionMeasurement',
    'SmokingPoint', 'SmokingPointValue', 'SmokingPointMeasurement',
    'ThermalExpansion', 'CoefficientOfThermalExpansion', 'TMAMeasurement'
]

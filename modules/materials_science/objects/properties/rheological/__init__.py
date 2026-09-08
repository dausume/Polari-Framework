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
Rheological Properties Module

Rheological properties relate to the flow and deformation of matter.

Property Modules:
- viscosity/: Viscosity → KrebsViscosity → StormerViscosity
- elasticity/: Elasticity → StorageModulus → DMA/Rheometer measurements
- meltFlowIndex/: MeltFlowIndex → MFIValue → MFIMeasurement
"""

from materials_science.objects.properties.rheological.rheologicalProperty import RheologicalProperty

from materials_science.objects.properties.rheological.viscosity import (
    Viscosity, KrebsViscosity, StormerViscosity
)
from materials_science.objects.properties.rheological.elasticity import (
    Elasticity, StorageModulus, DMAMeasurement, RheometerMeasurement
)
from materials_science.objects.properties.rheological.meltFlowIndex import (
    MeltFlowIndex, MFIValue, MFIMeasurement
)

__all__ = [
    'RheologicalProperty',
    'Viscosity', 'KrebsViscosity', 'StormerViscosity',
    'Elasticity', 'StorageModulus', 'DMAMeasurement', 'RheometerMeasurement',
    'MeltFlowIndex', 'MFIValue', 'MFIMeasurement'
]

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
Surface Properties Module

Surface properties relate to interfacial phenomena between materials.

Property Modules:
- solidSurfaceEnergy/: SolidSurfaceEnergy → CriticalSurfaceTension → ContactAngleMeasurement
- liquidSurfaceTension/: LiquidSurfaceTension → SurfaceTensionValue → WilhelmyMeasurement
"""

from polariMaterialsScienceModule.properties.surface.surfaceProperty import SurfaceProperty

from polariMaterialsScienceModule.properties.surface.solidSurfaceEnergy import (
    SolidSurfaceEnergy, CriticalSurfaceTension, ContactAngleMeasurement
)
from polariMaterialsScienceModule.properties.surface.liquidSurfaceTension import (
    LiquidSurfaceTension, SurfaceTensionValue, WilhelmyMeasurement
)

__all__ = [
    'SurfaceProperty',
    'SolidSurfaceEnergy', 'CriticalSurfaceTension', 'ContactAngleMeasurement',
    'LiquidSurfaceTension', 'SurfaceTensionValue', 'WilhelmyMeasurement'
]

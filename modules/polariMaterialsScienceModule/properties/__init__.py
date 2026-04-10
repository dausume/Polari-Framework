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
Material Properties Module

This module organizes material properties by category:

Categories:
- rheological/: Flow and deformation properties (viscosity, elasticity, MFI)
- mechanical/: Strength and resistance properties (hardness, tensile strength)
- surface/: Interfacial properties (surface energy, surface tension)
- thermal/: Temperature-dependent properties (melting point, Tg, CTE)
- physical/: Basic physical properties (specific gravity/density)

Each property follows the abstraction hierarchy:
- Level 1: Abstract property concept
- Level 2: Derived/standard value
- Level 3: Raw measurement datapoints

All measurement classes include:
- Documentation references to standards (ASTM, ISO)
- Open source/DIY implementation references
- openSourceImplementationExists boolean flag
"""

from polariMaterialsScienceModule.properties.propertyCategory import PropertyCategory

# Import categories
from polariMaterialsScienceModule.properties.rheological import RheologicalProperty
from polariMaterialsScienceModule.properties.mechanical import MechanicalProperty
from polariMaterialsScienceModule.properties.surface import SurfaceProperty
from polariMaterialsScienceModule.properties.thermal import ThermalProperty

# Import rheological properties
from polariMaterialsScienceModule.properties.rheological.viscosity import (
    Viscosity, KrebsViscosity, StormerViscosity
)
from polariMaterialsScienceModule.properties.rheological.elasticity import (
    Elasticity, StorageModulus, DMAMeasurement, RheometerMeasurement
)
from polariMaterialsScienceModule.properties.rheological.meltFlowIndex import (
    MeltFlowIndex, MFIValue, MFIMeasurement
)

# Import mechanical properties
from polariMaterialsScienceModule.properties.mechanical.hardness import (
    Hardness, HardnessScale, ShoreMeasurement
)
from polariMaterialsScienceModule.properties.mechanical.tensileStrength import (
    TensileStrength, UltimateTensileStrength, TensileMeasurement
)

# Import surface properties
from polariMaterialsScienceModule.properties.surface.solidSurfaceEnergy import (
    SolidSurfaceEnergy, CriticalSurfaceTension, ContactAngleMeasurement
)
from polariMaterialsScienceModule.properties.surface.liquidSurfaceTension import (
    LiquidSurfaceTension, SurfaceTensionValue, WilhelmyMeasurement
)

# Import thermal properties
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

# Import physical properties
from polariMaterialsScienceModule.properties.physical.specificGravity import (
    SpecificGravity, ReferentialSpecificGravity,
    PycnometerMeasurement, HydrometerMeasurement, DensityMeterMeasurement
)

__all__ = [
    # Base
    'PropertyCategory',

    # Categories
    'RheologicalProperty',
    'MechanicalProperty',
    'SurfaceProperty',
    'ThermalProperty',

    # Rheological
    'Viscosity', 'KrebsViscosity', 'StormerViscosity',
    'Elasticity', 'StorageModulus', 'DMAMeasurement', 'RheometerMeasurement',
    'MeltFlowIndex', 'MFIValue', 'MFIMeasurement',

    # Mechanical
    'Hardness', 'HardnessScale', 'ShoreMeasurement',
    'TensileStrength', 'UltimateTensileStrength', 'TensileMeasurement',

    # Surface
    'SolidSurfaceEnergy', 'CriticalSurfaceTension', 'ContactAngleMeasurement',
    'LiquidSurfaceTension', 'SurfaceTensionValue', 'WilhelmyMeasurement',

    # Thermal
    'MeltingPoint', 'MeltingPointValue', 'DSCMeltingMeasurement',
    'GlassTransition', 'GlassTransitionTemp', 'DMAGlassTransitionMeasurement',
    'SmokingPoint', 'SmokingPointValue', 'SmokingPointMeasurement',
    'ThermalExpansion', 'CoefficientOfThermalExpansion', 'TMAMeasurement',

    # Physical
    'SpecificGravity', 'ReferentialSpecificGravity',
    'PycnometerMeasurement', 'HydrometerMeasurement', 'DensityMeterMeasurement'
]

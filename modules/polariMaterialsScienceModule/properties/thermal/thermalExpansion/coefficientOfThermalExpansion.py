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
CoefficientOfThermalExpansion Model

Represents a derived Coefficient of Thermal Expansion (CTE) value.
Inherits from ThermalExpansion at abstraction level 2.

CTE calculation:
- α = (1/L₀) × (dL/dT) in 1/°C
- Often reported in ppm/°C (10⁻⁶/°C) or µm/(m·°C)
- Mean CTE: Average over temperature range
- Instantaneous CTE: Slope at specific temperature

Temperature ranges:
- Often specified over a range (e.g., 25-100°C)
- CTE changes through glass transition (polymers)
- May need multiple ranges for full characterization

Standards References:
- ASTM E831: TMA - Standard test method
- ASTM D696: Plastics - Between -30 and 30°C
- ASTM E228: Vitreous silica dilatometer method
- ISO 11359-2: TMA - Determination of CTE
- Typical heating rate: 5°C/min

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: ThermalExpansion (abstract concept)
    - Level 2: CoefficientOfThermalExpansion (this class - derived value)
    - Level 3: TMAMeasurement (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.thermalExpansion.thermalExpansion import ThermalExpansion


class CoefficientOfThermalExpansion(ThermalExpansion):
    """
    Derived Coefficient of Thermal Expansion value (Level 2).

    Represents the CTE in ppm/°C (or 10⁻⁶/°C) calculated from
    TMA or dilatometer measurements.

    Abstraction level: 2

    Attributes:
        ctePpmPerC: CTE in ppm/°C (parts per million per degree Celsius)
        temperatureRangeLowC: Low end of temperature range
        temperatureRangeHighC: High end of temperature range
        expansionType: Type (linear, volumetric)
        direction: Direction for anisotropic materials (X, Y, Z, or isotropic)
        measurementMethod: Method used (TMA, dilatometer)
        heatingRate: Heating rate in °C/min
        measurementDate: Date when value was derived
        notes: Additional notes
    """

    ABSTRACTION_LEVEL = 2

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 ctePpmPerC=0.0,
                 temperatureRangeLowC=25.0,
                 temperatureRangeHighC=100.0,
                 expansionType='linear',
                 direction='isotropic',
                 measurementMethod='TMA',
                 heatingRate=5.0,
                 measurementDate='',
                 notes=''):
        ThermalExpansion.__init__(self, manager=manager, branch=branch, id=id,
                                  name='Coefficient of Thermal Expansion',
                                  description='Derived CTE in ppm/°C',
                                  materialId=materialId)
        self.ctePpmPerC = ctePpmPerC
        self.temperatureRangeLowC = temperatureRangeLowC
        self.temperatureRangeHighC = temperatureRangeHighC
        self.expansionType = expansionType
        self.direction = direction
        self.measurementMethod = measurementMethod
        self.heatingRate = heatingRate
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_from_measurements(self, measurements, original_length_mm):
        """
        Calculate mean CTE from TMA measurements.

        Args:
            measurements: List of TMAMeasurement objects with temperature and dimension change
            original_length_mm: Original sample length in mm

        Returns:
            float: Calculated CTE in ppm/°C
        """
        if not measurements or len(measurements) < 2 or original_length_mm <= 0:
            return self.ctePpmPerC

        # Sort by temperature
        sorted_measurements = sorted(measurements, key=lambda m: m.temperatureC)
        first = sorted_measurements[0]
        last = sorted_measurements[-1]

        delta_L = last.dimensionChangeMicron - first.dimensionChangeMicron
        delta_T = last.temperatureC - first.temperatureC

        if delta_T > 0:
            # CTE = (ΔL/L₀)/ΔT, convert to ppm
            self.ctePpmPerC = (delta_L / (original_length_mm * 1000)) / delta_T * 1e6
            self.temperatureRangeLowC = first.temperatureC
            self.temperatureRangeHighC = last.temperatureC

        return self.ctePpmPerC

    def __repr__(self):
        return f"CoefficientOfThermalExpansion(id='{self.id}', materialId='{self.materialId}', CTE={self.ctePpmPerC} ppm/°C)"

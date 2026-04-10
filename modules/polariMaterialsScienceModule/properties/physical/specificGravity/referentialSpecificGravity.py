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
ReferentialSpecificGravity Model

Level 2 - Derived specific gravity normalized against a reference material.

Common reference materials:
- Water at 4°C (most common for liquids/solids, density = 1.000 g/cm³)
- Water at 20°C (density ≈ 0.998 g/cm³)
- Air at STP (for gases)
- Oil (various industrial standards)

The specific gravity value is dimensionless since it's a ratio of densities.
A ReferentialSpecificGravity record represents the final derived specific gravity
for a material, computed from raw measurement datapoints.

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
- Level 1: SpecificGravity (abstract specific gravity concept)
- Level 2: ReferentialSpecificGravity (this class - normalized against reference)
- Level 3: Raw measurements (Pycnometer, Hydrometer, DensityMeter, etc.)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.physical.specificGravity.specificGravity import SpecificGravity


class ReferentialSpecificGravity(SpecificGravity):
    """
    Derived specific gravity normalized against a reference material.

    This represents a specific gravity value computed from raw measurements
    and normalized against a standard reference material (water, oil, air, etc.).

    Common reference standards:
    - 'water_4C': Water at 4°C (density = 1.000 g/cm³)
    - 'water_20C': Water at 20°C (density ≈ 0.998 g/cm³)
    - 'air_STP': Air at standard temperature and pressure
    - 'oil': Various industrial oil standards

    Abstraction level: 2

    Attributes:
        specificGravityValue: The derived specific gravity (dimensionless ratio)
        referenceMaterial: The reference material used for normalization
        referenceTemperature: Temperature of reference material (Celsius)
        sampleTemperature: Temperature of sample during measurement (Celsius)
        measurementDate: Date when the value was derived
        notes: Additional notes about the derived value
    """

    ABSTRACTION_LEVEL = 2

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 specificGravityValue=0.0,
                 referenceMaterial='water_4C',
                 referenceTemperature=4.0,
                 sampleTemperature=25.0,
                 measurementDate='',
                 notes=''):
        SpecificGravity.__init__(self, manager=manager, branch=branch, id=id,
                                 name='Referential Specific Gravity',
                                 description='Specific gravity normalized against reference material',
                                 materialId=materialId)
        self.specificGravityValue = specificGravityValue
        self.referenceMaterial = referenceMaterial
        self.referenceTemperature = referenceTemperature
        self.sampleTemperature = sampleTemperature
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_from_measurements(self, measurements):
        """
        Calculate specific gravity from a set of raw measurements.

        Args:
            measurements: List of raw measurement objects (Pycnometer, Hydrometer, etc.)

        Returns:
            float: Calculated specific gravity value
        """
        if not measurements:
            return self.specificGravityValue

        total_sg = 0.0
        count = 0
        for measurement in measurements:
            if hasattr(measurement, 'specificGravityValue') and measurement.specificGravityValue > 0:
                total_sg += measurement.specificGravityValue
                count += 1

        if count > 0:
            self.specificGravityValue = total_sg / count

        return self.specificGravityValue

    def __repr__(self):
        return f"ReferentialSpecificGravity(id='{self.id}', materialId='{self.materialId}', value={self.specificGravityValue}, ref='{self.referenceMaterial}')"

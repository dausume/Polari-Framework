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
DensityMeterMeasurement Model

Level 3 - Raw specific gravity measurement using a digital density meter.

Digital density meters typically use the oscillating U-tube method (based on
ASTM D4052, ISO 15212). A U-shaped glass tube is filled with sample and
electronically excited to oscillate. The oscillation frequency changes with
the density of the sample, allowing precise density/specific gravity measurement.

Advantages:
- High precision (typically ±0.0001 g/cm³)
- Small sample volume required (1-2 mL)
- Temperature controlled
- Automated measurement

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
- Level 1: SpecificGravity (abstract specific gravity concept)
- Level 2: ReferentialSpecificGravity (normalized against reference)
- Level 3: DensityMeterMeasurement (this class - raw measurement)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.physical.specificGravity.specificGravity import SpecificGravity


class DensityMeterMeasurement(SpecificGravity):
    """
    Raw specific gravity measurement using a digital density meter.

    Digital density meters use oscillating tube technology to measure
    density with high precision, then convert to specific gravity.

    Abstraction level: 3 (most specific)

    Attributes:
        referentialSpecificGravityId: ID reference to parent ReferentialSpecificGravity
        sequenceNumber: Order of this measurement within a set
        densityValue: Measured density (g/cm³)
        specificGravityValue: Calculated specific gravity
        oscillationFrequency: Raw oscillation frequency (Hz) if available
        temperature: Measurement temperature (Celsius)
        referenceDensity: Density of reference material at measurement temp (g/cm³)
        measurementDate: Date of measurement (ISO format string)
        operator: Name of the person who took the measurement
        equipment: Density meter model/identifier
        calibrationDate: Last calibration date
        notes: Additional notes about the measurement
    """

    ABSTRACTION_LEVEL = 3

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 referentialSpecificGravityId='',
                 sequenceNumber=0,
                 densityValue=0.0,
                 specificGravityValue=0.0,
                 oscillationFrequency=0.0,
                 temperature=25.0,
                 referenceDensity=0.99707,
                 measurementDate='',
                 operator='',
                 equipment='',
                 calibrationDate='',
                 notes=''):
        SpecificGravity.__init__(self, manager=manager, branch=branch, id=id,
                                 name='Density Meter Measurement',
                                 description='Raw digital density meter measurement',
                                 materialId=materialId)
        self.referentialSpecificGravityId = referentialSpecificGravityId
        self.sequenceNumber = sequenceNumber
        self.densityValue = densityValue
        self.specificGravityValue = specificGravityValue
        self.oscillationFrequency = oscillationFrequency
        self.temperature = temperature
        self.referenceDensity = referenceDensity  # Water at 25°C ≈ 0.99707 g/cm³
        self.measurementDate = measurementDate
        self.operator = operator
        self.equipment = equipment
        self.calibrationDate = calibrationDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_specific_gravity(self):
        """
        Calculate specific gravity from measured density.

        SG = sample density / reference density

        Returns:
            float: Calculated specific gravity
        """
        if self.referenceDensity > 0 and self.densityValue > 0:
            self.specificGravityValue = self.densityValue / self.referenceDensity

        return self.specificGravityValue

    def __repr__(self):
        return f"DensityMeterMeasurement(id='{self.id}', materialId='{self.materialId}', density={self.densityValue}, SG={self.specificGravityValue})"

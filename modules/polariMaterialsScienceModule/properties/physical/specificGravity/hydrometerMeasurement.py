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
HydrometerMeasurement Model

Level 3 - Raw specific gravity measurement using a hydrometer.

A hydrometer is a floating instrument that measures the specific gravity
(relative density) of liquids based on the principle of buoyancy. The depth
to which the hydrometer sinks in the liquid indicates the specific gravity,
read directly from a calibrated scale on the stem.

Different hydrometers are calibrated for different ranges and applications:
- General purpose (0.700 - 2.000)
- Baume scale (for sugar solutions, acids, etc.)
- API scale (petroleum industry)
- Brix scale (sugar content)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
- Level 1: SpecificGravity (abstract specific gravity concept)
- Level 2: ReferentialSpecificGravity (normalized against reference)
- Level 3: HydrometerMeasurement (this class - raw measurement)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.physical.specificGravity.specificGravity import SpecificGravity


class HydrometerMeasurement(SpecificGravity):
    """
    Raw specific gravity measurement using a hydrometer.

    A hydrometer floats in the liquid and the specific gravity is read
    directly from the calibrated scale at the liquid surface.

    Abstraction level: 3 (most specific)

    Attributes:
        referentialSpecificGravityId: ID reference to parent ReferentialSpecificGravity
        sequenceNumber: Order of this measurement within a set
        scaleReading: Direct reading from hydrometer scale
        specificGravityValue: Specific gravity (may equal scaleReading or be converted)
        scaleType: Type of scale ('SG', 'Baume', 'API', 'Brix', etc.)
        temperature: Temperature during measurement (Celsius)
        calibrationTemperature: Temperature hydrometer is calibrated for (Celsius)
        measurementDate: Date of measurement (ISO format string)
        operator: Name of the person who took the measurement
        equipment: Hydrometer identifier/model
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
                 scaleReading=0.0,
                 specificGravityValue=0.0,
                 scaleType='SG',
                 temperature=25.0,
                 calibrationTemperature=20.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes=''):
        SpecificGravity.__init__(self, manager=manager, branch=branch, id=id,
                                 name='Hydrometer Measurement',
                                 description='Raw hydrometer specific gravity measurement',
                                 materialId=materialId)
        self.referentialSpecificGravityId = referentialSpecificGravityId
        self.sequenceNumber = sequenceNumber
        self.scaleReading = scaleReading
        self.specificGravityValue = specificGravityValue
        self.scaleType = scaleType
        self.temperature = temperature
        self.calibrationTemperature = calibrationTemperature
        self.measurementDate = measurementDate
        self.operator = operator
        self.equipment = equipment
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def convert_to_specific_gravity(self):
        """
        Convert scale reading to specific gravity if needed.

        For 'SG' scale, the reading is already specific gravity.
        Other scales (Baume, API, Brix) require conversion formulas.

        Returns:
            float: Specific gravity value
        """
        if self.scaleType == 'SG':
            self.specificGravityValue = self.scaleReading
        elif self.scaleType == 'Baume_heavy':
            # For liquids heavier than water: SG = 145 / (145 - Baume)
            if self.scaleReading < 145:
                self.specificGravityValue = 145.0 / (145.0 - self.scaleReading)
        elif self.scaleType == 'Baume_light':
            # For liquids lighter than water: SG = 140 / (130 + Baume)
            self.specificGravityValue = 140.0 / (130.0 + self.scaleReading)
        elif self.scaleType == 'API':
            # API gravity: SG = 141.5 / (131.5 + API)
            self.specificGravityValue = 141.5 / (131.5 + self.scaleReading)
        else:
            # Default: assume reading is specific gravity
            self.specificGravityValue = self.scaleReading

        return self.specificGravityValue

    def __repr__(self):
        return f"HydrometerMeasurement(id='{self.id}', materialId='{self.materialId}', reading={self.scaleReading}, scale='{self.scaleType}')"

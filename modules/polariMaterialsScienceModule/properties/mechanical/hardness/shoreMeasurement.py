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
ShoreMeasurement Model

Represents a single datapoint from a Shore durometer measurement.
Inherits from HardnessScale at abstraction level 3 (most specific).

A durometer measures the depth of indentation created by a standardized
indentor under a specified force. Shore scales differ in indentor geometry
and spring force:

- Shore A: Truncated cone, 822 g force, for soft elastomers
- Shore D: Sharp cone, 4536 g force, for hard plastics
- Shore OO: Hemisphere, 113 g force, for very soft gels/foams

Procedure:
1. Condition sample to test temperature (typically 23°C)
2. Place durometer perpendicular to surface
3. Apply full force (press firmly)
4. Read value at 1 second or 15 seconds (per specification)
5. Take multiple readings at different locations

Standards References:
- ASTM D2240: Standard test method for rubber property - Durometer hardness
- ISO 868: Plastics - Determination of indentation hardness by durometer
- ISO 7619-1: Rubber - Determination of indentation hardness

Open Source / DIY References:
- RepRap Durometer: 3D printable durometer designs (limited accuracy)
- Arduino Shore Tester: Load cell + LVDT based designs
- Most DIY versions achieve ±5 units accuracy vs ±1 for commercial
- Analog durometers are relatively affordable (~$50-200)
- Digital durometers with data logging available (~$200-500)

openSourceImplementationExists: True (DIY designs exist, limited precision)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - MechanicalProperty (strength/resistance category)
    - Level 1: Hardness (abstract concept)
    - Level 2: HardnessScale (derived/standard value)
    - Level 3: ShoreMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.mechanical.hardness.hardnessScale import HardnessScale


class ShoreMeasurement(HardnessScale):
    """
    Shore durometer measurement datapoint (most specific raw measurement).

    Captures a single Shore hardness reading from a durometer test.

    Abstraction level: 3 (most specific)

    Attributes:
        hardnessScaleId: ID reference to parent HardnessScale this contributes to
        sequenceNumber: Order of this reading within the test set
        hardnessReading: Shore hardness reading (0-100)
        shoreType: Shore scale type (A, D, OO, etc.)
        readingTime: Time after contact for reading (1s or 15s typical)
        sampleThickness: Sample thickness in mm (minimum 6mm typically)
        locationOnSample: Description of measurement location
        temperature: Temperature during measurement (Celsius)
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: Durometer model used
        notes: Additional notes
        openSourceImplementationExists: Whether DIY/open source version exists
    """

    ABSTRACTION_LEVEL = 3

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 hardnessScaleId='',
                 sequenceNumber=0,
                 hardnessReading=0.0,
                 shoreType='A',
                 readingTime=1.0,
                 sampleThickness=6.0,
                 locationOnSample='',
                 temperature=23.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes='',
                 openSourceImplementationExists=True):
        HardnessScale.__init__(self, manager=manager, branch=branch, id=id,
                               materialId=materialId,
                               hardnessValue=hardnessReading,
                               scale=f'Shore {shoreType}',
                               temperature=temperature,
                               measurementDate=measurementDate,
                               notes=notes)
        self.hardnessScaleId = hardnessScaleId
        self.sequenceNumber = sequenceNumber
        self.hardnessReading = hardnessReading
        self.shoreType = shoreType
        self.readingTime = readingTime
        self.sampleThickness = sampleThickness
        self.locationOnSample = locationOnSample
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"ShoreMeasurement(id='{self.id}', materialId='{self.materialId}', reading={self.hardnessReading} Shore {self.shoreType})"

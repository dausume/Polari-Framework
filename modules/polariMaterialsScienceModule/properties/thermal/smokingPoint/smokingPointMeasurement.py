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
SmokingPointMeasurement Model

Represents a single smoking point measurement datapoint.
Inherits from SmokingPointValue at abstraction level 3 (most specific).

Measurement procedure (AOCS Cc 9a-48):
1. Place sample in open cup (Cleveland or similar)
2. Heat at controlled rate (5-6°C/min for oils)
3. Observe for first wisp of continuous smoke
4. Record temperature when smoke is visible

Visual observation criteria:
- Distinct wisp of smoke rising from surface
- Continuous, not sporadic
- Distinguish from steam (water vapor)

Automated alternatives:
- Optical smoke detection (photoelectric)
- Temperature control with automated heating

Standards References:
- AOCS Cc 9a-48: American Oil Chemists' Society method
- ASTM D92: Cleveland open cup apparatus
- ISO 2592: Petroleum products (similar apparatus)
- Cup dimensions: 68.5mm diameter, 33.3mm depth (Cleveland)

Open Source / DIY References:
- Simple setup: Hot plate + thermometer + open cup
- Arduino smoke detector: Photoelectric or laser-based
- Food science community: Many DIY smoke point testers
- Cost: Commercial ~$500-2000; DIY <$50

openSourceImplementationExists: True (very accessible DIY method)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: SmokingPoint (abstract concept)
    - Level 2: SmokingPointValue (derived/standard value)
    - Level 3: SmokingPointMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.smokingPoint.smokingPointValue import SmokingPointValue


class SmokingPointMeasurement(SmokingPointValue):
    """
    Smoking point measurement datapoint (most specific raw measurement).

    Captures a single smoke point observation from visual or automated detection.

    Abstraction level: 3 (most specific)

    Attributes:
        smokingPointValueId: ID reference to parent SmokingPointValue
        sequenceNumber: Order of this measurement (if repeated)
        observedTemperatureC: Temperature when smoke first observed
        cupType: Cup type used (Cleveland, Pensky-Martens)
        sampleVolumeMl: Sample volume in mL
        heatingRate: Heating rate in °C/min
        ambientTemperature: Room temperature in Celsius
        humidity: Relative humidity (%)
        detectionMethod: Detection type (visual, photoelectric, laser)
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: Equipment used
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
                 smokingPointValueId='',
                 sequenceNumber=0,
                 observedTemperatureC=0.0,
                 cupType='Cleveland open cup',
                 sampleVolumeMl=75.0,
                 heatingRate=5.0,
                 ambientTemperature=23.0,
                 humidity=50.0,
                 detectionMethod='visual',
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes='',
                 openSourceImplementationExists=True):
        SmokingPointValue.__init__(self, manager=manager, branch=branch, id=id,
                                   materialId=materialId,
                                   smokingPointC=observedTemperatureC,
                                   measurementMethod=detectionMethod,
                                   heatingRate=heatingRate,
                                   measurementDate=measurementDate,
                                   notes=notes)
        self.smokingPointValueId = smokingPointValueId
        self.sequenceNumber = sequenceNumber
        self.observedTemperatureC = observedTemperatureC
        self.cupType = cupType
        self.sampleVolumeMl = sampleVolumeMl
        self.ambientTemperature = ambientTemperature
        self.humidity = humidity
        self.detectionMethod = detectionMethod
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"SmokingPointMeasurement(id='{self.id}', materialId='{self.materialId}', T={self.observedTemperatureC}°C)"

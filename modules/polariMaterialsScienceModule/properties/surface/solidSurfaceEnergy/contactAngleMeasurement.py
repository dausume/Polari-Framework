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
ContactAngleMeasurement Model

Represents a single contact angle measurement datapoint.
Inherits from CriticalSurfaceTension at abstraction level 3 (most specific).

A contact angle goniometer measures the angle formed between a liquid
droplet and a solid surface. The angle indicates wettability:
- θ < 90°: Hydrophilic (wetting)
- θ > 90°: Hydrophobic (non-wetting)
- θ → 0°: Complete wetting
- θ → 180°: Complete non-wetting

Measurement modes:
- Static: Sessile drop at equilibrium
- Advancing: Angle as drop expands
- Receding: Angle as drop contracts
- Hysteresis: Advancing - Receding

Standards References:
- ASTM D5946: Standard test method for corona-treated polymer films
- ASTM D7490: Water contact angle measurement
- ISO 19403-2: Contact angle measurement procedures
- Drop volume: Typically 2-10 µL for sessile drop

Open Source / DIY References:
- OpenDrop: github.com/opendrop (open source contact angle software)
- Krüss DSA alternative: DIY goniometer + OpenDrop software
- ImageJ Contact Angle: Plugin for analyzing droplet images
- DIY Setup: USB microscope + syringe + LED backlight
- Python libraries: contact-angle, droplet-analysis
- Cost: Commercial goniometers $10k-50k; DIY <$500

openSourceImplementationExists: True (OpenDrop software is excellent)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - SurfaceProperty (interfacial phenomena category)
    - Level 1: SolidSurfaceEnergy (abstract concept)
    - Level 2: CriticalSurfaceTension (derived/standard value)
    - Level 3: ContactAngleMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.surface.solidSurfaceEnergy.criticalSurfaceTension import CriticalSurfaceTension


class ContactAngleMeasurement(CriticalSurfaceTension):
    """
    Contact angle measurement datapoint (most specific raw measurement).

    Captures a single contact angle reading from a goniometer measurement.

    Abstraction level: 3 (most specific)

    Attributes:
        surfaceEnergyId: ID reference to parent CriticalSurfaceTension
        sequenceNumber: Order of this measurement within the set
        contactAngle: Measured contact angle in degrees
        probeLiquid: Probe liquid used (water, diiodomethane, etc.)
        probeLiquidSurfaceTension: Surface tension of probe in mN/m
        dropVolume: Drop volume in µL
        measurementType: Type (static, advancing, receding)
        leftAngle: Left side angle in degrees (if asymmetric)
        rightAngle: Right side angle in degrees (if asymmetric)
        humidity: Relative humidity during measurement (%)
        temperature: Temperature during measurement (Celsius)
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: Goniometer model used
        software: Analysis software used
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
                 surfaceEnergyId='',
                 sequenceNumber=0,
                 contactAngle=0.0,
                 probeLiquid='water',
                 probeLiquidSurfaceTension=72.8,
                 dropVolume=5.0,
                 measurementType='static',
                 leftAngle=0.0,
                 rightAngle=0.0,
                 humidity=50.0,
                 temperature=23.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 software='',
                 notes='',
                 openSourceImplementationExists=True):
        CriticalSurfaceTension.__init__(self, manager=manager, branch=branch, id=id,
                                        materialId=materialId,
                                        surfaceEnergyMNm=0.0,
                                        temperature=temperature,
                                        measurementDate=measurementDate,
                                        notes=notes)
        self.surfaceEnergyId = surfaceEnergyId
        self.sequenceNumber = sequenceNumber
        self.contactAngle = contactAngle
        self.probeLiquid = probeLiquid
        self.probeLiquidSurfaceTension = probeLiquidSurfaceTension
        self.dropVolume = dropVolume
        self.measurementType = measurementType
        self.leftAngle = leftAngle
        self.rightAngle = rightAngle
        self.humidity = humidity
        self.operator = operator
        self.equipment = equipment
        self.software = software
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_average_angle(self):
        """Calculate average angle from left and right measurements."""
        if self.leftAngle > 0 and self.rightAngle > 0:
            self.contactAngle = (self.leftAngle + self.rightAngle) / 2
        return self.contactAngle

    def __repr__(self):
        return f"ContactAngleMeasurement(id='{self.id}', materialId='{self.materialId}', θ={self.contactAngle}° ({self.probeLiquid})"

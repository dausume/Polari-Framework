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
TensileMeasurement Model

Represents a single datapoint from a tensile test.
Inherits from UltimateTensileStrength at abstraction level 3 (most specific).

A Universal Testing Machine (UTM) pulls a specimen at controlled rate
while measuring force and displacement. The stress-strain curve is
built from these datapoints.

Test procedure:
1. Prepare dog-bone shaped specimen per ASTM D638 or similar
2. Measure initial dimensions (gauge length, width, thickness)
3. Mount specimen in grips
4. Zero force and displacement
5. Apply tensile load at specified crosshead speed
6. Record force-displacement data until specimen breaks
7. Calculate stress-strain from raw data

Standards References:
- ASTM D638: Detailed specimen preparation and test procedures
- ASTM E8/E8M: Metallic materials tensile testing
- ISO 527: International standard for plastics
- Specimen conditioning: 40 hrs at 23°C, 50% RH typical

Open Source / DIY References:
- OpenSource UTM: github.com/opensourceutm (DIY tensile tester)
- HackaDay projects: Multiple Arduino-based tensile testers
- RepRap community: Filament tensile testers for QC
- OpenFlexure: Microscope with tensile testing module
- Typical DIY: Stepper motor + load cell (5-500 kg) + linear rail
- Commercial alternatives: Instron, MTS, Shimadzu (expensive)

openSourceImplementationExists: True (multiple DIY designs available)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - MechanicalProperty (strength/resistance category)
    - Level 1: TensileStrength (abstract concept)
    - Level 2: UltimateTensileStrength (derived/standard value)
    - Level 3: TensileMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.mechanical.tensileStrength.ultimateTensileStrength import UltimateTensileStrength


class TensileMeasurement(UltimateTensileStrength):
    """
    Tensile test measurement datapoint (most specific raw measurement).

    Captures a single force-displacement datapoint from a tensile test.

    Abstraction level: 3 (most specific)

    Attributes:
        utsId: ID reference to parent UltimateTensileStrength this contributes to
        sequenceNumber: Order of this datapoint within the test
        forceN: Applied force in Newtons
        displacementMm: Crosshead displacement in mm
        time: Time from test start in seconds
        gaugeLength: Original gauge length in mm
        specimenWidth: Specimen width in mm
        specimenThickness: Specimen thickness in mm
        extensometerStrain: Strain from extensometer (if used)
        temperature: Temperature during measurement (Celsius)
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: UTM model used
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
                 utsId='',
                 sequenceNumber=0,
                 forceN=0.0,
                 displacementMm=0.0,
                 time=0.0,
                 gaugeLength=50.0,
                 specimenWidth=13.0,
                 specimenThickness=3.2,
                 extensometerStrain=0.0,
                 testSpeed=5.0,
                 temperature=23.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes='',
                 openSourceImplementationExists=True):
        UltimateTensileStrength.__init__(self, manager=manager, branch=branch, id=id,
                                         materialId=materialId,
                                         utsMPa=0.0,
                                         testSpeed=testSpeed,
                                         temperature=temperature,
                                         measurementDate=measurementDate,
                                         notes=notes)
        self.utsId = utsId
        self.sequenceNumber = sequenceNumber
        self.forceN = forceN
        self.displacementMm = displacementMm
        self.time = time
        self.gaugeLength = gaugeLength
        self.specimenWidth = specimenWidth
        self.specimenThickness = specimenThickness
        self.extensometerStrain = extensometerStrain
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_engineering_stress(self):
        """Calculate engineering stress in MPa."""
        area = self.specimenWidth * self.specimenThickness
        if area > 0:
            return self.forceN / area
        return 0.0

    def calculate_engineering_strain(self):
        """Calculate engineering strain as percentage."""
        if self.gaugeLength > 0:
            return (self.displacementMm / self.gaugeLength) * 100
        return 0.0

    def __repr__(self):
        return f"TensileMeasurement(id='{self.id}', materialId='{self.materialId}', force={self.forceN}N, disp={self.displacementMm}mm)"

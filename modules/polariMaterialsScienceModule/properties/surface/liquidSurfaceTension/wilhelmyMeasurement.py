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
WilhelmyMeasurement Model

Represents a single Wilhelmy plate tensiometer measurement.
Inherits from SurfaceTensionValue at abstraction level 3 (most specific).

The Wilhelmy plate method measures force on a thin plate partially
immersed in liquid. The plate is typically platinum or glass, roughened
to ensure complete wetting (contact angle = 0).

Calculation:
γ = F / (2L) when θ = 0
Where:
- γ: Surface tension (mN/m)
- F: Force measured (mN)
- L: Plate perimeter (mm) = 2(width + thickness)

Advantages:
- No need to know contact angle (if plate is completely wet)
- Can measure dynamic surface tension
- Good for surfactant solutions

Standards References:
- ASTM D1331: Standard test methods for surface tension
- ISO 304: Surface active agents - Wilhelmy plate method
- Plate dimensions: Typically 20mm x 10mm x 0.1mm (Pt)

Open Source / DIY References:
- DIY Wilhelmy: Precision balance + platinum plate
- Arduino tensiometer: Load cell + linear actuator designs
- OpenSourceTensiometer: github projects for DIY tensiometers
- Cost: Commercial ~$5k-20k; DIY <$500 with precision balance

openSourceImplementationExists: True (DIY designs using precision balances)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - SurfaceProperty (interfacial phenomena category)
    - Level 1: LiquidSurfaceTension (abstract concept)
    - Level 2: SurfaceTensionValue (derived/standard value)
    - Level 3: WilhelmyMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.surface.liquidSurfaceTension.surfaceTensionValue import SurfaceTensionValue


class WilhelmyMeasurement(SurfaceTensionValue):
    """
    Wilhelmy plate measurement datapoint (most specific raw measurement).

    Captures a single force reading from a Wilhelmy plate tensiometer.

    Abstraction level: 3 (most specific)

    Attributes:
        surfaceTensionValueId: ID reference to parent SurfaceTensionValue
        sequenceNumber: Order of this measurement within the set
        forceMN: Force measured in mN
        platePerimeterMm: Plate perimeter in mm
        plateMaterial: Plate material (platinum, glass)
        contactAngle: Contact angle if not completely wetting (degrees)
        immersionDepthMm: Depth of plate immersion in mm
        temperature: Temperature during measurement (Celsius)
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: Tensiometer model used
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
                 surfaceTensionValueId='',
                 sequenceNumber=0,
                 forceMN=0.0,
                 platePerimeterMm=40.2,
                 plateMaterial='platinum',
                 contactAngle=0.0,
                 immersionDepthMm=0.0,
                 temperature=20.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes='',
                 openSourceImplementationExists=True):
        SurfaceTensionValue.__init__(self, manager=manager, branch=branch, id=id,
                                     materialId=materialId,
                                     surfaceTensionMNm=0.0,
                                     measurementMethod='Wilhelmy plate',
                                     temperature=temperature,
                                     measurementDate=measurementDate,
                                     notes=notes)
        self.surfaceTensionValueId = surfaceTensionValueId
        self.sequenceNumber = sequenceNumber
        self.forceMN = forceMN
        self.platePerimeterMm = platePerimeterMm
        self.plateMaterial = plateMaterial
        self.contactAngle = contactAngle
        self.immersionDepthMm = immersionDepthMm
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

        # Calculate surface tension
        self._calculate_surface_tension()

    def _calculate_surface_tension(self):
        """Calculate surface tension from force and plate perimeter."""
        import math
        if self.platePerimeterMm > 0:
            cos_theta = math.cos(math.radians(self.contactAngle))
            if cos_theta > 0:
                self.surfaceTensionMNm = self.forceMN / (self.platePerimeterMm * cos_theta)

    def __repr__(self):
        return f"WilhelmyMeasurement(id='{self.id}', materialId='{self.materialId}', F={self.forceMN}mN, γ={self.surfaceTensionMNm} mN/m)"

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
TMAMeasurement Model

Represents a single TMA (Thermomechanical Analysis) measurement datapoint.
Inherits from CoefficientOfThermalExpansion at abstraction level 3 (most specific).

TMA measures dimensional changes of a sample under controlled temperature
and load conditions. A probe contacts the sample surface and tracks
position changes as temperature varies.

TMA modes:
- Expansion: Minimal load, measure thermal expansion
- Penetration: Higher load, detect softening point
- Tension: Thin films, fibers

Typical setup:
- Sample geometry: Cylinder or rectangular bar
- Length: 5-10 mm typical
- Probe force: 0.01-0.05 N for expansion
- Temperature range: -150 to 1000°C depending on instrument

Standards References:
- ASTM E831: Standard test method for TMA
- ASTM E1545: Softening point by TMA
- ISO 11359-2: TMA - Determination of CTE
- Sample preparation: Flat, parallel surfaces critical

Open Source / DIY References:
- DIY TMA: LVDT + furnace + load control
- Arduino-based thermal expansion meters
- Precision is challenging; micrometer resolution needed
- Commercial TMA: TA Instruments, Mettler, Netzsch ($20k-80k)
- Alternative: Simple dilatometer with dial gauge (less precise)

openSourceImplementationExists: True (DIY designs exist, limited precision)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: ThermalExpansion (abstract concept)
    - Level 2: CoefficientOfThermalExpansion (derived/standard value)
    - Level 3: TMAMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.thermalExpansion.coefficientOfThermalExpansion import CoefficientOfThermalExpansion


class TMAMeasurement(CoefficientOfThermalExpansion):
    """
    TMA measurement datapoint (most specific raw measurement).

    Captures a single datapoint from a TMA temperature scan.

    Abstraction level: 3 (most specific)

    Attributes:
        cteId: ID reference to parent CoefficientOfThermalExpansion
        sequenceNumber: Order of this datapoint within the scan
        temperatureC: Temperature in Celsius
        dimensionChangeMicron: Dimensional change in micrometers
        time: Time from scan start in seconds
        originalLengthMm: Original sample length in mm
        probeForceN: Applied probe force in Newtons
        probeType: Probe geometry (expansion, penetration)
        atmosphere: Purge gas (nitrogen, air)
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: TMA model used
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
                 cteId='',
                 sequenceNumber=0,
                 temperatureC=0.0,
                 dimensionChangeMicron=0.0,
                 time=0.0,
                 originalLengthMm=10.0,
                 probeForceN=0.02,
                 probeType='expansion',
                 atmosphere='nitrogen',
                 heatingRate=5.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes='',
                 openSourceImplementationExists=True):
        CoefficientOfThermalExpansion.__init__(self, manager=manager, branch=branch, id=id,
                                               materialId=materialId,
                                               ctePpmPerC=0.0,
                                               measurementMethod='TMA',
                                               heatingRate=heatingRate,
                                               measurementDate=measurementDate,
                                               notes=notes)
        self.cteId = cteId
        self.sequenceNumber = sequenceNumber
        self.temperatureC = temperatureC
        self.dimensionChangeMicron = dimensionChangeMicron
        self.time = time
        self.originalLengthMm = originalLengthMm
        self.probeForceN = probeForceN
        self.probeType = probeType
        self.atmosphere = atmosphere
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_strain_percent(self):
        """Calculate engineering strain as percentage."""
        if self.originalLengthMm > 0:
            return (self.dimensionChangeMicron / (self.originalLengthMm * 1000)) * 100
        return 0.0

    def __repr__(self):
        return f"TMAMeasurement(id='{self.id}', materialId='{self.materialId}', T={self.temperatureC}°C, ΔL={self.dimensionChangeMicron}µm)"

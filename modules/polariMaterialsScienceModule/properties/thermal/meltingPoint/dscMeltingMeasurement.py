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
DSCMeltingMeasurement Model

Represents a single DSC measurement datapoint for melting analysis.
Inherits from MeltingPointValue at abstraction level 3 (most specific).

DSC measures heat flow into/out of a sample as temperature changes:
- Endothermic peaks: Melting, glass transition
- Exothermic peaks: Crystallization, curing, decomposition
- Heat flow units: mW or W/g

DSC types:
- Heat flux DSC: Sample and reference on single furnace
- Power compensation DSC: Separate heaters maintain equal temperature
- Modulated DSC (MDSC): Sinusoidal temperature program

Standards References:
- ASTM D3418: Detailed DSC procedures for polymers
- ASTM E967: Temperature calibration of DSC
- ASTM E968: Heat flow calibration of DSC
- ISO 11357-1: General principles for DSC
- Sample mass: Typically 5-10 mg for polymers

Open Source / DIY References:
- OpenDSC: Attempts at DIY DSC (very challenging)
- Arduino thermal analysis: Basic DTA possible
- Commercial DSC: TA Instruments, Mettler, Netzsch ($10k-100k)
- Alternative: Visual capillary tube method for melting point only
- University shared equipment: Often accessible for research

openSourceImplementationExists: False (precision DSC is very difficult DIY)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: MeltingPoint (abstract concept)
    - Level 2: MeltingPointValue (derived/standard value)
    - Level 3: DSCMeltingMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.meltingPoint.meltingPointValue import MeltingPointValue


class DSCMeltingMeasurement(MeltingPointValue):
    """
    DSC melting measurement datapoint (most specific raw measurement).

    Captures a single datapoint from a DSC temperature scan.

    Abstraction level: 3 (most specific)

    Attributes:
        meltingPointValueId: ID reference to parent MeltingPointValue
        sequenceNumber: Order of this datapoint within the scan
        temperatureC: Temperature in Celsius
        heatFlowMW: Heat flow in mW (or mW/mg if normalized)
        time: Time from scan start in seconds
        sampleMassMg: Sample mass in mg
        panType: Sample pan type (aluminum, hermetic, etc.)
        atmosphere: Purge gas (nitrogen, air)
        flowRateMlMin: Purge gas flow rate in mL/min
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: DSC model used
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
                 meltingPointValueId='',
                 sequenceNumber=0,
                 temperatureC=0.0,
                 heatFlowMW=0.0,
                 time=0.0,
                 sampleMassMg=10.0,
                 panType='aluminum',
                 atmosphere='nitrogen',
                 flowRateMlMin=50.0,
                 heatingRate=10.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes='',
                 openSourceImplementationExists=False):
        MeltingPointValue.__init__(self, manager=manager, branch=branch, id=id,
                                   materialId=materialId,
                                   meltingPointC=0.0,
                                   measurementMethod='DSC',
                                   heatingRate=heatingRate,
                                   measurementDate=measurementDate,
                                   notes=notes)
        self.meltingPointValueId = meltingPointValueId
        self.sequenceNumber = sequenceNumber
        self.temperatureC = temperatureC
        self.heatFlowMW = heatFlowMW
        self.time = time
        self.sampleMassMg = sampleMassMg
        self.panType = panType
        self.atmosphere = atmosphere
        self.flowRateMlMin = flowRateMlMin
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def normalize_heat_flow(self):
        """Normalize heat flow to sample mass (mW/mg)."""
        if self.sampleMassMg > 0:
            return self.heatFlowMW / self.sampleMassMg
        return 0.0

    def __repr__(self):
        return f"DSCMeltingMeasurement(id='{self.id}', materialId='{self.materialId}', T={self.temperatureC}°C, HF={self.heatFlowMW}mW)"

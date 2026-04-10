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
DMAGlassTransitionMeasurement Model

Represents a single DMA measurement datapoint for glass transition analysis.
Inherits from GlassTransitionTemp at abstraction level 3 (most specific).

DMA is often preferred for Tg determination because:
- Higher sensitivity than DSC for small Tg changes
- Provides mechanical property data (modulus vs temperature)
- tan(δ) peak is well-defined and reproducible
- Can detect multiple transitions (α, β, γ relaxations)

Key DMA parameters at Tg:
- E' (Storage Modulus): Drops 2-3 decades through Tg region
- E'' (Loss Modulus): Shows peak at Tg
- tan(δ) = E''/E': Shows peak at slightly higher temperature

Standards References:
- ASTM D7028: DMA procedures for Tg determination
- ASTM E1640: Tg by DMA
- ISO 6721-11: DMA - Determination of Tg
- Typical frequency: 1 Hz for standard Tg
- Heating rate: 2-5°C/min (slower than DSC for thermal equilibrium)

Open Source / DIY References:
- DIY DMA is possible with stepper motor + load cell + temperature control
- OpenDMA projects exist for educational purposes
- Precision is limited but useful for comparative studies
- Commercial DMA: TA Instruments, Mettler ($30k-100k)

openSourceImplementationExists: True (educational/approximate DIY versions)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: GlassTransition (abstract concept)
    - Level 2: GlassTransitionTemp (derived/standard value)
    - Level 3: DMAGlassTransitionMeasurement (this class - raw measurement)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.glassTransition.glassTransitionTemp import GlassTransitionTemp


class DMAGlassTransitionMeasurement(GlassTransitionTemp):
    """
    DMA glass transition measurement datapoint (most specific raw measurement).

    Captures a single datapoint from a DMA temperature scan for Tg analysis.

    Abstraction level: 3 (most specific)

    Attributes:
        glassTransitionTempId: ID reference to parent GlassTransitionTemp
        sequenceNumber: Order of this datapoint within the scan
        temperatureC: Temperature in Celsius
        storageModulusPa: Storage modulus E' in Pa
        lossModulusPa: Loss modulus E'' in Pa
        tanDelta: Loss factor tan(δ) = E''/E'
        frequency: Oscillation frequency in Hz
        strain: Applied strain amplitude (%)
        clampType: Clamping geometry
        sampleLength: Sample length in mm
        sampleWidth: Sample width in mm
        sampleThickness: Sample thickness in mm
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: DMA model used
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
                 glassTransitionTempId='',
                 sequenceNumber=0,
                 temperatureC=0.0,
                 storageModulusPa=0.0,
                 lossModulusPa=0.0,
                 tanDelta=0.0,
                 frequency=1.0,
                 strain=0.1,
                 clampType='single cantilever',
                 sampleLength=0.0,
                 sampleWidth=0.0,
                 sampleThickness=0.0,
                 heatingRate=3.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes='',
                 openSourceImplementationExists=True):
        GlassTransitionTemp.__init__(self, manager=manager, branch=branch, id=id,
                                     materialId=materialId,
                                     tgCelsius=0.0,
                                     measurementMethod='DMA-tanδ',
                                     heatingRate=heatingRate,
                                     frequency=frequency,
                                     measurementDate=measurementDate,
                                     notes=notes)
        self.glassTransitionTempId = glassTransitionTempId
        self.sequenceNumber = sequenceNumber
        self.temperatureC = temperatureC
        self.storageModulusPa = storageModulusPa
        self.lossModulusPa = lossModulusPa
        self.tanDelta = tanDelta
        self.strain = strain
        self.clampType = clampType
        self.sampleLength = sampleLength
        self.sampleWidth = sampleWidth
        self.sampleThickness = sampleThickness
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_tan_delta(self):
        """Calculate tan(δ) from storage and loss moduli."""
        if self.storageModulusPa > 0:
            self.tanDelta = self.lossModulusPa / self.storageModulusPa
        return self.tanDelta

    def __repr__(self):
        return f"DMAGlassTransitionMeasurement(id='{self.id}', materialId='{self.materialId}', T={self.temperatureC}°C, tanδ={self.tanDelta})"

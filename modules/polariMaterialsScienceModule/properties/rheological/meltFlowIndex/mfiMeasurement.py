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
MFIMeasurement Model

Represents a single datapoint from a melt flow index extrusion plastometer
measurement. Inherits from MFIValue at abstraction level 3 (most specific).

An extrusion plastometer (melt indexer) consists of:
- Heated barrel with temperature control
- Die with standardized orifice (2.095 mm diameter)
- Piston with specified weight on top
- Sample loaded in barrel, melted, extruded through die

Procedure (ASTM D1238 - Procedure A):
1. Load sample into heated barrel
2. Allow thermal equilibration (typically 4-6 minutes)
3. Apply specified weight load
4. Cut extrudate at timed intervals
5. Weigh extruded sections
6. Calculate g/10min

Standards References:
- ASTM D1238: Standard test method for MFR of thermoplastics
- ISO 1133-1: Plastics - MFR and MVR determination
- Die dimensions: 2.095 ± 0.005 mm diameter, 8.000 ± 0.025 mm length

Open Source / DIY References:
- RepRap MFI Tester: DIY designs using PID-controlled heating elements
- Arduino MFI: Temperature control with load cell for timing
- Filastruder community: DIY testers for filament production QC
- OpenMFI: github.com/openmfi (community project, check availability)
- Academic publications: "Low-cost melt flow indexer for educational use"

openSourceImplementationExists: True (multiple DIY designs available)

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: MeltFlowIndex (abstract concept)
    - Level 2: MFIValue (derived/standard value)
    - Level 3: MFIMeasurement (this class - raw measurement datapoint)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.meltFlowIndex.mfiValue import MFIValue


class MFIMeasurement(MFIValue):
    """
    Extrusion plastometer measurement datapoint (most specific raw measurement).

    Captures a single extrusion cut from an MFI test, including the
    extruded mass and time interval.

    Abstraction level: 3 (most specific)

    Attributes:
        mfiValueId: ID reference to parent MFIValue this contributes to
        sequenceNumber: Order of this cut within the test set
        extrusionTime: Time interval for this extrusion in seconds
        extrudateMass: Mass of extrudate in grams
        preheatTime: Preheat/equilibration time in seconds
        barrelTemperature: Actual barrel temperature in Celsius
        dieDiameter: Die orifice diameter in mm
        dieLength: Die length in mm
        measurementDate: Date of measurement
        operator: Person who performed measurement
        equipment: Melt indexer model used
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
                 mfiValueId='',
                 sequenceNumber=0,
                 extrusionTime=0.0,
                 extrudateMass=0.0,
                 preheatTime=300.0,
                 barrelTemperature=190.0,
                 testLoad=2.16,
                 dieDiameter=2.095,
                 dieLength=8.0,
                 measurementDate='',
                 operator='',
                 equipment='',
                 notes='',
                 openSourceImplementationExists=True):
        MFIValue.__init__(self, manager=manager, branch=branch, id=id,
                          materialId=materialId,
                          mfiGramsPer10Min=0.0,
                          testTemperature=barrelTemperature,
                          testLoad=testLoad,
                          measurementDate=measurementDate,
                          notes=notes)
        self.mfiValueId = mfiValueId
        self.sequenceNumber = sequenceNumber
        self.extrusionTime = extrusionTime
        self.extrudateMass = extrudateMass
        self.preheatTime = preheatTime
        self.barrelTemperature = barrelTemperature
        self.dieDiameter = dieDiameter
        self.dieLength = dieLength
        self.operator = operator
        self.equipment = equipment
        self.openSourceImplementationExists = openSourceImplementationExists
        self.abstractionLevel = self.ABSTRACTION_LEVEL

        # Calculate instantaneous MFI for this cut
        if self.extrusionTime > 0:
            self.mfiGramsPer10Min = (self.extrudateMass / self.extrusionTime) * 600

    def __repr__(self):
        return f"MFIMeasurement(id='{self.id}', materialId='{self.materialId}', mass={self.extrudateMass}g, time={self.extrusionTime}s)"

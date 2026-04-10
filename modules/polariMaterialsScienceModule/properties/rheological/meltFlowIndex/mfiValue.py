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
MFIValue Model

Represents a derived Melt Flow Index value in g/10min.
Inherits from MeltFlowIndex at abstraction level 2.

MFI is reported in grams per 10 minutes (g/10min) at a specific
temperature and load combination. Common conditions:

Polyethylene (PE):
- 190°C / 2.16 kg (standard condition)
- 190°C / 21.6 kg (high load, for HLMI/FRR)

Polypropylene (PP):
- 230°C / 2.16 kg

ABS, PC, Nylon:
- Various conditions per ASTM D1238 tables

Flow Rate Ratio (FRR):
- HLMI / MI = indication of molecular weight distribution
- Broader MWD = higher FRR

Standards References:
- ASTM D1238: Procedure A (mass method), Procedure B (volume method)
- ISO 1133-1: MFR (mass) and MVR (volume) procedures
- ISO 1133-2: Determination of time to rheological stability

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: MeltFlowIndex (abstract concept)
    - Level 2: MFIValue (this class - derived/standard value)
    - Level 3: MFIMeasurement (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.rheological.meltFlowIndex.meltFlowIndex import MeltFlowIndex


class MFIValue(MeltFlowIndex):
    """
    Derived Melt Flow Index value (Level 2).

    Represents a standardized MFI value in g/10min calculated from
    raw extrusion plastometer measurements.

    Abstraction level: 2

    Attributes:
        mfiGramsPer10Min: MFI value in g/10min
        testTemperature: Test temperature in Celsius (e.g., 190 for PE)
        testLoad: Applied load in kg (e.g., 2.16 kg standard)
        polymerType: Type of polymer tested (PE, PP, ABS, etc.)
        measurementDate: Date when value was derived
        notes: Additional notes
    """

    ABSTRACTION_LEVEL = 2

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 mfiGramsPer10Min=0.0,
                 testTemperature=190.0,
                 testLoad=2.16,
                 polymerType='',
                 measurementDate='',
                 notes=''):
        MeltFlowIndex.__init__(self, manager=manager, branch=branch, id=id,
                               name='MFI Value',
                               description='Derived Melt Flow Index in g/10min',
                               materialId=materialId)
        self.mfiGramsPer10Min = mfiGramsPer10Min
        self.testTemperature = testTemperature
        self.testLoad = testLoad
        self.polymerType = polymerType
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_from_measurements(self, measurements):
        """
        Calculate MFI from a set of MFIMeasurement objects.

        The standard procedure involves averaging multiple extrusions
        and normalizing to g/10min.

        Args:
            measurements: List of MFIMeasurement objects

        Returns:
            float: Calculated MFI in g/10min
        """
        if not measurements:
            return self.mfiGramsPer10Min

        total_rate = 0.0
        count = 0
        for m in measurements:
            if m.extrudateMass > 0 and m.extrusionTime > 0:
                # Normalize to g/10min
                rate = (m.extrudateMass / m.extrusionTime) * 600
                total_rate += rate
                count += 1

        if count > 0:
            self.mfiGramsPer10Min = total_rate / count

        return self.mfiGramsPer10Min

    def __repr__(self):
        return f"MFIValue(id='{self.id}', materialId='{self.materialId}', MFI={self.mfiGramsPer10Min} g/10min @ {self.testTemperature}°C/{self.testLoad}kg)"

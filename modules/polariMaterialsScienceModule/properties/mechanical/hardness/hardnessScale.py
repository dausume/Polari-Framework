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
HardnessScale Model

Represents a derived hardness value on a specific scale.
Inherits from Hardness at abstraction level 2.

Common hardness scales:
- Shore A: Soft elastomers (0-100 scale)
- Shore D: Hard elastomers and plastics (0-100 scale)
- Shore OO: Very soft gels and foams (0-100 scale)
- Rockwell B: Soft metals (steel ball, 100 kg load)
- Rockwell C: Hard metals (diamond cone, 150 kg load)
- Vickers HV: Universal (diamond pyramid, various loads)
- Brinell HB: Metals (steel ball, various loads)
- Pencil: Coatings (6B-6H scale)

Standards References:
- ASTM D2240: Shore hardness scales and procedures
- ASTM E18: Rockwell scales and procedures
- ASTM E384: Vickers/Knoop microhardness procedures
- ISO 868: Plastics - Determination of indentation hardness

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - MechanicalProperty (strength/resistance category)
    - Level 1: Hardness (abstract concept)
    - Level 2: HardnessScale (this class - derived/standard value)
    - Level 3: ShoreMeasurement, RockwellMeasurement, VickersMeasurement
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.mechanical.hardness.hardness import Hardness


class HardnessScale(Hardness):
    """
    Derived hardness value on a specific scale (Level 2).

    Represents a hardness value on a standardized scale (Shore, Rockwell,
    Vickers, etc.) calculated from raw indentation measurements.

    Abstraction level: 2

    Attributes:
        hardnessValue: Numeric hardness value
        scale: Hardness scale used (Shore A, Shore D, Rockwell C, Vickers, etc.)
        temperature: Reference temperature in Celsius
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
                 hardnessValue=0.0,
                 scale='Shore A',
                 temperature=23.0,
                 measurementDate='',
                 notes=''):
        Hardness.__init__(self, manager=manager, branch=branch, id=id,
                          name='Hardness Scale',
                          description=f'Derived hardness on {scale} scale',
                          materialId=materialId)
        self.hardnessValue = hardnessValue
        self.scale = scale
        self.temperature = temperature
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def calculate_from_measurements(self, measurements):
        """
        Calculate average hardness from a set of measurements.

        Hardness is typically reported as the average of multiple readings
        taken at different locations on the sample.

        Args:
            measurements: List of measurement objects with hardnessReading attribute

        Returns:
            float: Average hardness value
        """
        if not measurements:
            return self.hardnessValue

        total = 0.0
        count = 0
        for m in measurements:
            if hasattr(m, 'hardnessReading') and m.hardnessReading > 0:
                total += m.hardnessReading
                count += 1

        if count > 0:
            self.hardnessValue = total / count

        return self.hardnessValue

    def __repr__(self):
        return f"HardnessScale(id='{self.id}', materialId='{self.materialId}', value={self.hardnessValue} {self.scale})"

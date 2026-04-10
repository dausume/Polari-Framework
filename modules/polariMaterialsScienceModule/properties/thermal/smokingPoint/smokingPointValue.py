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
SmokingPointValue Model

Represents a derived smoking point temperature in Celsius.
Inherits from SmokingPoint at abstraction level 2.

Reference smoking points for common oils:
- Extra virgin olive oil: 160-190°C
- Refined olive oil: 210-240°C
- Coconut oil (refined): 204°C
- Avocado oil: 270°C
- Flaxseed oil: 107°C
- Butter: 150°C
- Ghee: 250°C

For industrial materials:
- Paraffin wax: 200-300°C
- Mineral oil: 200-260°C
- Silicone oil: 300-400°C

Standards References:
- AOCS Cc 9a-48: Official methods for smoke point determination
- Cleveland open cup method (ASTM D92, ISO 2592)
- Sample size: Typically 75-100 mL
- Heating rate: 5-6°C/min for oils

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: SmokingPoint (abstract concept)
    - Level 2: SmokingPointValue (this class - derived value)
    - Level 3: SmokingPointMeasurement (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.smokingPoint.smokingPoint import SmokingPoint


class SmokingPointValue(SmokingPoint):
    """
    Derived smoking point value (Level 2).

    Represents the smoking point temperature in Celsius from
    visual observation or automated detection.

    Abstraction level: 2

    Attributes:
        smokingPointC: Smoking point in Celsius
        flashPointC: Flash point in Celsius (if also measured)
        firePointC: Fire point in Celsius (if also measured)
        measurementMethod: Method used (visual, automated)
        heatingRate: Heating rate in °C/min
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
                 smokingPointC=0.0,
                 flashPointC=0.0,
                 firePointC=0.0,
                 measurementMethod='visual',
                 heatingRate=5.0,
                 measurementDate='',
                 notes=''):
        SmokingPoint.__init__(self, manager=manager, branch=branch, id=id,
                              name='Smoking Point Value',
                              description='Derived smoking point in Celsius',
                              materialId=materialId)
        self.smokingPointC = smokingPointC
        self.flashPointC = flashPointC
        self.firePointC = firePointC
        self.measurementMethod = measurementMethod
        self.heatingRate = heatingRate
        self.measurementDate = measurementDate
        self.notes = notes
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"SmokingPointValue(id='{self.id}', materialId='{self.materialId}', smoke={self.smokingPointC}°C)"

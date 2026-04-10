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
SmokingPoint Model

Represents the abstract concept of smoking point - the temperature at
which a material begins to produce visible smoke due to thermal degradation.
Inherits from ThermalProperty at abstraction level 1.

Smoking point is distinct from:
- Flash point: Temperature of vapors that can ignite with external flame
- Fire point: Temperature of sustained combustion
- Decomposition temperature: Full thermal breakdown

Applications:
- Cooking oils (food science)
- Lubricants (automotive, industrial)
- Waxes and coatings
- Polymers (processing limit)
- Resins (curing and degassing)

Factors affecting smoking point:
- Free fatty acid content (oils)
- Refining level
- Water content
- Impurities and additives
- Previous thermal history (degraded oils smoke sooner)

Standards References:
- AOCS Cc 9a-48: Smoke, flash, and fire points of fats and oils
- ASTM D92: Cleveland open cup flash point
- ISO 2592: Petroleum products - Flash and fire point
- COC and open-cup methods for smoking point

Open Source References:
- Simple visual observation method is accessible
- Thermocouple + oil bath + visual inspection
- DIY smoke point testers for cooking oils
- Food science community has accessible methods

Abstraction Levels:
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: SmokingPoint (this class - abstract concept)
    - Level 2: SmokingPointValue (derived/standard value)
    - Level 3: SmokingPointMeasurement (raw measurement datapoints)
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.properties.thermal.thermalProperty import ThermalProperty


class SmokingPoint(ThermalProperty):
    """
    Abstract smoking point property (Level 1).

    Represents the concept of smoking point - the temperature at which
    a material begins to produce visible smoke from thermal degradation.

    Abstraction level: 1 (abstract concept)

    Attributes:
        materialId: ID reference to the parent Material
    """

    ABSTRACTION_LEVEL = 1

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 name='Smoking Point',
                 description='Temperature at which material produces visible smoke',
                 materialId=''):
        ThermalProperty.__init__(self, manager=manager, branch=branch, id=id,
                                 name=name, description=description,
                                 materialId=materialId)
        self.abstractionLevel = self.ABSTRACTION_LEVEL

    def __repr__(self):
        return f"SmokingPoint(id='{self.id}', materialId='{self.materialId}')"

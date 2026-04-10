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
Melt Flow Index Module

Provides MFI-related models with a clear abstraction hierarchy:

Abstraction Levels (0 = most abstract, higher = more specific):
- Level 0: MaterialProperty (core reference)
  - RheologicalProperty (flow/deformation category)
    - Level 1: MeltFlowIndex (abstract MFI concept)
    - Level 2: MFIValue (derived/computed MFI in g/10min)
    - Level 3: MFIMeasurement (raw extrusion plastometer datapoints)
"""

from polariMaterialsScienceModule.properties.rheological.meltFlowIndex.meltFlowIndex import MeltFlowIndex
from polariMaterialsScienceModule.properties.rheological.meltFlowIndex.mfiValue import MFIValue
from polariMaterialsScienceModule.properties.rheological.meltFlowIndex.mfiMeasurement import MFIMeasurement

__all__ = [
    'MeltFlowIndex',
    'MFIValue',
    'MFIMeasurement'
]

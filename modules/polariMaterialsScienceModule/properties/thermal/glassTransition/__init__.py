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
Glass Transition Module

Provides glass transition-related models with a clear abstraction hierarchy:

Abstraction Levels (0 = most abstract, higher = more specific):
- Level 0: MaterialProperty (core reference)
  - ThermalProperty (temperature-dependent category)
    - Level 1: GlassTransition (abstract Tg concept)
    - Level 2: GlassTransitionTemp (derived/computed Tg in Celsius)
    - Level 3: DMAGlassTransitionMeasurement (raw DMA measurement datapoints)
"""

from polariMaterialsScienceModule.properties.thermal.glassTransition.glassTransition import GlassTransition
from polariMaterialsScienceModule.properties.thermal.glassTransition.glassTransitionTemp import GlassTransitionTemp
from polariMaterialsScienceModule.properties.thermal.glassTransition.dmaGlassTransitionMeasurement import DMAGlassTransitionMeasurement

__all__ = [
    'GlassTransition',
    'GlassTransitionTemp',
    'DMAGlassTransitionMeasurement'
]

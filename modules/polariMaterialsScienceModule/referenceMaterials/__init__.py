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
Reference Materials Module

Well-characterized materials with documented property values from
various sources (academic, manufacturer, community).

Structure:
- ReferenceMaterial: Base class for all reference materials
- PropertyValueSource: Cited property values with source information
- threeDimensionalPrintable/: FDM 3D printable reference materials
  - PLA, ABS, PETG, Nylon, TPU, PHA
"""

from polariMaterialsScienceModule.referenceMaterials.referenceMaterial import ReferenceMaterial
from polariMaterialsScienceModule.referenceMaterials.propertyValueSource import PropertyValueSource

# 3D Printable reference materials
from polariMaterialsScienceModule.referenceMaterials.threeDimensionalPrintable import (
    PrintableReferenceMaterial,
    PLA, ABS, PETG, Nylon, TPU, PHA
)

__all__ = [
    # Base classes
    'ReferenceMaterial',
    'PropertyValueSource',

    # 3D Printable materials
    'PrintableReferenceMaterial',
    'PLA',
    'ABS',
    'PETG',
    'Nylon',
    'TPU',
    'PHA'
]

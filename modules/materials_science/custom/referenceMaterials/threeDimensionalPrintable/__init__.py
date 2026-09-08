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
3D Printable Reference Materials

Reference materials commonly used in FDM 3D printing with documented
property values and typical printing parameters.

Materials:
- PLA: Polylactic Acid - easiest to print, biodegradable
- ABS: Acrylonitrile Butadiene Styrene - strong, requires enclosure
- PETG: Glycol-modified PET - balance of printability and strength
- Nylon: Polyamide - strong, flexible, very hygroscopic
- TPU: Thermoplastic Polyurethane - flexible, rubber-like
- PHA: Polyhydroxyalkanoate - biodegradable, marine-safe
"""

from materials_science.custom.referenceMaterials.threeDimensionalPrintable.printableReferenceMaterial import PrintableReferenceMaterial
from materials_science.custom.referenceMaterials.threeDimensionalPrintable.pla import PLA
from materials_science.custom.referenceMaterials.threeDimensionalPrintable.abs import ABS
from materials_science.custom.referenceMaterials.threeDimensionalPrintable.petg import PETG
from materials_science.custom.referenceMaterials.threeDimensionalPrintable.nylon import Nylon
from materials_science.custom.referenceMaterials.threeDimensionalPrintable.tpu import TPU
from materials_science.custom.referenceMaterials.threeDimensionalPrintable.pha import PHA

__all__ = [
    'PrintableReferenceMaterial',
    'PLA',
    'ABS',
    'PETG',
    'Nylon',
    'TPU',
    'PHA'
]

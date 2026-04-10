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
3D Printed Mold Materials Module

Defines composite material suitability for 3D printing fine-resolution molds.
"""

from polariMaterialsScienceModule.purposes.moldFabrication.threeDimensionalPrintedMold.threeDimensionalPrintedMoldMaterial import ThreeDimensionalPrintedMoldMaterial
from polariMaterialsScienceModule.purposes.moldFabrication.threeDimensionalPrintedMold.fdmPrintedMoldMaterial import FDMPrintedMoldMaterial
from polariMaterialsScienceModule.purposes.moldFabrication.threeDimensionalPrintedMold.slaPrintedMoldMaterial import SLAPrintedMoldMaterial
from polariMaterialsScienceModule.purposes.moldFabrication.threeDimensionalPrintedMold.slsPrintedMoldMaterial import SLSPrintedMoldMaterial

__all__ = [
    'ThreeDimensionalPrintedMoldMaterial',
    'FDMPrintedMoldMaterial',
    'SLAPrintedMoldMaterial',
    'SLSPrintedMoldMaterial'
]

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
Material Sourcing Module

Defines sourcing options for materials:
- MaterialSourcing: Base class for all sourcing types
- NaturalSourcing: Simple household-level extraction/refinement from natural sources
- OpenSourceLocalSourcing: More complex processes using open-source tools/designs
- CommercialSourcing: Purchasing from vendors (NOT mutually exclusive with above)

Note: CommercialSourcing can overlap with NaturalSourcing or OpenSourceLocalSourcing.
A vendor may use natural or open-source methods to produce what they sell commercially.
Use isCommercialOnly=True for vendors with proprietary-only production methods.
"""

from polariMaterialsScienceModule.materialSourcing.materialSourcing import MaterialSourcing
from polariMaterialsScienceModule.materialSourcing.naturalSourcing import NaturalSourcing
from polariMaterialsScienceModule.materialSourcing.openSourceLocalSourcing import OpenSourceLocalSourcing
from polariMaterialsScienceModule.materialSourcing.commercialSourcing import CommercialSourcing

__all__ = [
    'MaterialSourcing',
    'NaturalSourcing',
    'OpenSourceLocalSourcing',
    'CommercialSourcing'
]

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
Target Profiles Module

Desired property values for a specific use case.
Includes named profiles and individual property targets with
optimum values, ranges, and priority weights.
"""

from polariMaterialsScienceModule.targetProfiles.targetMaterialProfile import TargetMaterialProfile
from polariMaterialsScienceModule.targetProfiles.propertyTarget import PropertyTarget

__all__ = [
    'TargetMaterialProfile',
    'PropertyTarget'
]

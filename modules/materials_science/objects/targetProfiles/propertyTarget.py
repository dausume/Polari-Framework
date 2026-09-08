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
PropertyTarget Model

A single property target within a TargetMaterialProfile.
Defines desired value, acceptable range, and hard limits for one property.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PropertyTarget(treeObject):
    """
    A single property target within a profile.

    Attributes:
        profileId: ID of the TargetMaterialProfile this belongs to
        propertyName: Name of the target property
        optimumValue: Ideal value for this property
        optimumRangeMin: Minimum of acceptable optimum range
        optimumRangeMax: Maximum of acceptable optimum range
        hardMinimum: Absolute minimum acceptable value
        hardMaximum: Absolute maximum acceptable value
        weight: Priority weight 0-1 for optimization
        unit: Unit of measurement
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 profileId='',
                 propertyName='',
                 optimumValue=0.0,
                 optimumRangeMin=0.0,
                 optimumRangeMax=0.0,
                 hardMinimum=0.0,
                 hardMaximum=0.0,
                 weight=0.0,
                 unit=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.profileId = profileId
        self.propertyName = propertyName
        self.optimumValue = optimumValue
        self.optimumRangeMin = optimumRangeMin
        self.optimumRangeMax = optimumRangeMax
        self.hardMinimum = hardMinimum
        self.hardMaximum = hardMaximum
        self.weight = weight
        self.unit = unit

    def __repr__(self):
        return f"PropertyTarget(id='{getattr(self, 'id', '?')}', property='{getattr(self, 'propertyName', '?')}', optimum={getattr(self, 'optimumValue', '?')})"

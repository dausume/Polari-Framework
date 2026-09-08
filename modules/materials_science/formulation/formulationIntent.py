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
FormulationIntent Model

Desired property direction for a formulation.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class FormulationIntent(treeObject):
    """
    A desired property direction for a formulation.

    Attributes:
        formulationId: ID of the parent Formulation
        propertyName: Name of the target property
        direction: Desired direction (increase, decrease, maintain)
        priority: Priority level (critical, important, nice_to_have)
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 formulationId='',
                 propertyName='',
                 direction='',
                 priority=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.formulationId = formulationId
        self.propertyName = propertyName
        self.direction = direction
        self.priority = priority

    def __repr__(self):
        return f"FormulationIntent(id='{getattr(self, 'id', '?')}', property='{getattr(self, 'propertyName', '?')}', direction='{getattr(self, 'direction', '?')}')"

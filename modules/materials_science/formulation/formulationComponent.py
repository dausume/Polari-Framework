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
FormulationComponent Model

A single component in a formulation recipe with explicit role reporting.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class FormulationComponent(treeObject):
    """
    A component in a formulation recipe with explicit role declaration.

    Attributes:
        formulationId: ID of the parent Formulation
        materialId: ID of the RawMaterial used
        role: Role in the formulation (base, additive, compatibilizer)
        roleJustification: Explanation of why this role was assigned
        weightPercent: Weight percentage in the formulation
        orderOfAddition: Order in which this component is added
        mixingInstructions: Instructions for mixing this component
        expectedPropertyEffects: Comma-separated list of properties this component targets
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 formulationId='',
                 materialId='',
                 role='',
                 roleJustification='',
                 weightPercent=0.0,
                 orderOfAddition=0,
                 mixingInstructions='',
                 expectedPropertyEffects=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.formulationId = formulationId
        self.materialId = materialId
        self.role = role
        self.roleJustification = roleJustification
        self.weightPercent = weightPercent
        self.orderOfAddition = orderOfAddition
        self.mixingInstructions = mixingInstructions
        self.expectedPropertyEffects = expectedPropertyEffects

    def __repr__(self):
        return f"FormulationComponent(id='{getattr(self, 'id', '?')}', material='{getattr(self, 'materialId', '?')}', role='{getattr(self, 'role', '?')}', weight={getattr(self, 'weightPercent', '?')}%)"

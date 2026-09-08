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
PropertyEffect Model

How an additive affects a specific material property.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class PropertyEffect(treeObject):
    """
    Describes how an additive affects a specific property.

    Attributes:
        additiveId: ID of the MaterialAdditive
        propertyName: Name of affected property (e.g. 'Hardness')
        intent: Direction of effect ('+' for increase, '-' for decrease)
        normalizedEffectStrength: Effect strength normalized 0-1
        effectPerWeightPercent: Quantitative effect per weight percent added
        effectUnit: Unit for effectPerWeightPercent
        testConditions: Conditions under which effect was measured
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 additiveId='',
                 propertyName='',
                 intent='',
                 normalizedEffectStrength=0.0,
                 effectPerWeightPercent=0.0,
                 effectUnit='',
                 testConditions='',
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.additiveId = additiveId
        self.propertyName = propertyName
        self.intent = intent
        self.normalizedEffectStrength = normalizedEffectStrength
        self.effectPerWeightPercent = effectPerWeightPercent
        self.effectUnit = effectUnit
        self.testConditions = testConditions
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"PropertyEffect(id='{getattr(self, 'id', '?')}', additive='{getattr(self, 'additiveId', '?')}', property='{getattr(self, 'propertyName', '?')}', intent='{getattr(self, 'intent', '?')}')"

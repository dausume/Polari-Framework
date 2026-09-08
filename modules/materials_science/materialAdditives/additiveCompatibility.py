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
AdditiveCompatibility Model

Compatibility record between an additive and a base material.
"""

from objectTreeDecorators import treeObject, treeObjectInit


class AdditiveCompatibility(treeObject):
    """
    Compatibility between an additive and a base material.

    Attributes:
        additiveId: ID of the MaterialAdditive
        baseMaterialId: ID of the base RawMaterial
        compatible: Whether the combination is compatible
        requiresCompatibilizer: Whether a compatibilizer is needed
        compatibilizerId: ID of the Compatibilizer if required
        maxLoadingWithBase: Maximum loading percent with this specific base
        notes: Additional compatibility notes
        provenanceId: ID of the DataProvenance record
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 additiveId='',
                 baseMaterialId='',
                 compatible=False,
                 requiresCompatibilizer=False,
                 compatibilizerId='',
                 maxLoadingWithBase=0.0,
                 notes='',
                 provenanceId=''):
        treeObject.__init__(self, manager=manager, branch=branch, id=id)
        self.additiveId = additiveId
        self.baseMaterialId = baseMaterialId
        self.compatible = compatible
        self.requiresCompatibilizer = requiresCompatibilizer
        self.compatibilizerId = compatibilizerId
        self.maxLoadingWithBase = maxLoadingWithBase
        self.notes = notes
        self.provenanceId = provenanceId

    def __repr__(self):
        return f"AdditiveCompatibility(id='{getattr(self, 'id', '?')}', additive='{getattr(self, 'additiveId', '?')}', base='{getattr(self, 'baseMaterialId', '?')}', compatible={getattr(self, 'compatible', '?')})"

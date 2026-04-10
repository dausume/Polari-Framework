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
CoarsegrainedMolecularDynamicsMaterial Model

Represents a material using coarse-grained molecular dynamics (CGMD).
Multiple atoms are grouped into "beads" with effective interactions.

Common CGMD force fields:
- Martini: Biomolecules, lipids, polymers
- SDK (Shinoda-DeVane-Klein): General organic molecules
- TraPPE-CG: Hydrocarbons and polymers
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.mesoscale.mesoscaleResolution import MesoscaleResolution


class CoarsegrainedMolecularDynamicsMaterial(MesoscaleResolution):
    """
    Coarse-grained molecular dynamics material representation.

    Attributes:
        materialId: ID reference to the parent Material
        forceField: CGMD force field (martini, sdk, trappe-cg)
        beadMapping: Description of atom-to-bead mapping
        beadCount: Number of beads in the model
        moleculeTopology: Topology file reference
        interactionParameters: Interaction parameter file reference
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='CGMD Material',
                 description='Coarse-grained molecular dynamics representation',
                 forceField='martini',
                 beadMapping='',
                 beadCount=0,
                 moleculeTopology='',
                 interactionParameters=''):
        MesoscaleResolution.__init__(self, manager=manager, branch=branch, id=id,
                                     materialId=materialId,
                                     name=name, description=description)
        self.forceField = forceField
        self.beadMapping = beadMapping
        self.beadCount = beadCount
        self.moleculeTopology = moleculeTopology
        self.interactionParameters = interactionParameters

    def __repr__(self):
        return f"CoarsegrainedMolecularDynamicsMaterial(id='{self.id}', materialId='{self.materialId}', ff='{self.forceField}')"

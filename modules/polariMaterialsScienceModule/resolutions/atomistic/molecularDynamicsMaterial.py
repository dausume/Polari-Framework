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
MolecularDynamicsMaterial Model

Represents a material using classical molecular dynamics (MD).
Full atomistic representation with classical force fields.

Common MD force fields:
- AMBER: Biomolecules
- CHARMM: Biomolecules
- OPLS-AA: General organic molecules
- GAFF: General AMBER force field
- ReaxFF: Reactive force field
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.atomistic.atomisticResolution import AtomisticResolution


class MolecularDynamicsMaterial(AtomisticResolution):
    """
    Classical molecular dynamics material representation.

    Attributes:
        materialId: ID reference to the parent Material
        forceField: MD force field (amber, charmm, opls, gaff, reaxff)
        atomCount: Number of atoms in the model
        moleculeStructure: Structure file reference (PDB, GRO, etc.)
        topologyFile: Topology file reference
        parameterFile: Force field parameter file reference
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='MD Material',
                 description='Classical molecular dynamics representation',
                 forceField='opls-aa',
                 atomCount=0,
                 moleculeStructure='',
                 topologyFile='',
                 parameterFile=''):
        AtomisticResolution.__init__(self, manager=manager, branch=branch, id=id,
                                     materialId=materialId,
                                     name=name, description=description)
        self.forceField = forceField
        self.atomCount = atomCount
        self.moleculeStructure = moleculeStructure
        self.topologyFile = topologyFile
        self.parameterFile = parameterFile

    def __repr__(self):
        return f"MolecularDynamicsMaterial(id='{self.id}', materialId='{self.materialId}', ff='{self.forceField}')"

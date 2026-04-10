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
DensityFunctionalMaterial Model

Represents a material using density functional theory (DFT).
Full quantum mechanical treatment of electrons.

Common DFT functionals:
- LDA: Local density approximation
- GGA: Generalized gradient approximation (PBE, PW91)
- Hybrid: B3LYP, HSE
- Meta-GGA: SCAN, TPSS

Common DFT codes:
- VASP
- Quantum ESPRESSO
- Gaussian
- ORCA
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.resolutions.quantum.quantumResolution import QuantumResolution


class DensityFunctionalMaterial(QuantumResolution):
    """
    Density functional theory material representation.

    Attributes:
        materialId: ID reference to the parent Material
        functional: DFT functional (lda, pbe, b3lyp, hse)
        basisSet: Basis set (plane-wave cutoff or atomic basis)
        electronCount: Number of electrons
        structureFile: Structure file reference (POSCAR, XYZ, etc.)
        pseudopotentials: Pseudopotential files reference
        kPointMesh: k-point sampling mesh
    """

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 materialId='',
                 name='DFT Material',
                 description='Density functional theory representation',
                 functional='pbe',
                 basisSet='',
                 electronCount=0,
                 structureFile='',
                 pseudopotentials='',
                 kPointMesh=''):
        QuantumResolution.__init__(self, manager=manager, branch=branch, id=id,
                                   materialId=materialId,
                                   name=name, description=description)
        self.functional = functional
        self.basisSet = basisSet
        self.electronCount = electronCount
        self.structureFile = structureFile
        self.pseudopotentials = pseudopotentials
        self.kPointMesh = kPointMesh

    def __repr__(self):
        return f"DensityFunctionalMaterial(id='{self.id}', materialId='{self.materialId}', functional='{self.functional}')"

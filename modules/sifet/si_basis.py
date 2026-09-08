"""
@module sifet.si_basis

fp-2 object layer: silicon MOSFET decomposed into doping profiles,
a (thermal or sol-gel) gate dielectric, the sol-gel process, the
FET SHAPE (planar / SOI / FinFET / GAA) and the device row that
references them by name (cnt_basis style: decomposed objects, D8
roles, derived fields stamped with derived_at/provenance_json by
si_device.derive_si_device — never typed).

Sol-gel dielectric numbers are PRIORS from the open literature
(plan §2 decision 4) and say so on the row (confidence + citation).

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence + seeds)
    — to be wired by the integrator
  - sifet.custom.si_device, sifet.sifet_selftest
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/si/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from sifet.objects.si._shared import SEED_SI_DEVICES, SEED_SI_DIELECTRICS, SEED_SI_DOPINGS, SEED_SI_PROCESSES, SEED_SI_SHAPES, SEED_TABLES  # noqa: F401
from sifet.objects.si.SiliconDopingProfile import SiliconDopingProfile  # noqa: F401
from sifet.objects.si.SolGelDielectric import SolGelDielectric  # noqa: F401
from sifet.objects.si.SolGelProcess import SolGelProcess  # noqa: F401
from sifet.objects.si.SiliconFETShape import SiliconFETShape  # noqa: F401
from sifet.objects.si.SiliconMOSFET import SiliconMOSFET  # noqa: F401


SI_CLASSES = (SiliconDopingProfile, SolGelDielectric, SolGelProcess,
              SiliconFETShape, SiliconMOSFET)

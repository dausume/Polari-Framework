"""
@module meshassets.mesh_asset_basis

EXTERNAL MESH ASSETS AS LICENSE-GATED DATA (Dustin 2026-07-30:
"find a few samples of generic plant sub-morphologies that are
genuinely open source 3D models, which we can use as a pick and
choose 'close enough for approximation' mesh for simulations. So we
can fine tune them until they look similar enough to the original
using our morphology and part based definitions based on vectors").

The PlantMap3D evaluation is why this module exists at all: a paper
calling a tool "open source" was wrong, and the only thing that
settled it was reading the actual license. So license is not a note
here — it is a GATE with two levels, because the two questions are
genuinely different:

  compatible    do this licence's terms let a GPLv3 project use it?
  obligations   what must TRAVEL with it — attribution, share-alike?

Compatibility is judged RELATIVE TO OUR OWN LICENCE (GPL-3.0, see
PROJECT_LICENSE_SPDX), because compatibility is a relation between
two licences and never a property of one. Being GPLv3 ourselves is
what makes the copyleft assets usable: CC BY-SA 4.0 is one-way
compatible into GPLv3 by Creative Commons' own 2015 declaration,
and LGPL-2.1 section 3 relicenses to GPL. The genuinely blocking
cases are narrow: GPL-2.0-only, and NO LICENCE AT ALL — the
PlantMap3D case, where default copyright grants us nothing and our
own licence cannot invent permission the author never gave.

So the practical job here is not gatekeeping, it is CITATION:
every usable asset carries a complete, data-tracked credit
(Title, Author, Source, Licence + a link to the terms) that travels
with anything we ship. An asset whose licence requires attribution
but whose author or title is missing reports that GAP instead of
emitting a citation that looks complete and isn't.

THE APPROXIMATION IS THE POINT — for organic parts. A leaf has no
exact specification; "close enough, then tuned against our own
vector-based organ definition" is exactly right, and mesh_fit
measures HOW close rather than asserting it.

THE OPPOSITE IS TRUE FOR GEARS, and this module says so out loud:
a gear IS exactly specifiable (module, tooth count, pressure angle,
profile), and two gears only mesh if their specs agree. A
downloaded "close enough" gear is not an approximation, it is a
part that does not work. So gear geometry is GENERATED from our own
rows (GEARS_PLAN gr-3) and external gear assets are catalogued only
as ALGORITHM REFERENCES or as bought hardware we never make (a
worm, a bearing). `approximation_valid` on the source row carries
that distinction as data.

@consumers meshassets.custom.mesh_fit, meshassets.mesh_asset_api,
           plant_morphology (organ candidates), gears (references)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/mesh_asset/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from meshassets.objects.mesh_asset._shared import ASSET_SUBJECTS, COMPATIBILITY, PROJECT_LICENSE_SPDX, PROJECT_LICENSE_VERIFIED_FROM, VERIFICATION_METHODS  # noqa: F401
from meshassets.objects.mesh_asset.MeshAssetSource import MeshAssetSource  # noqa: F401
from meshassets.objects.mesh_asset.MeshAssetReference import MeshAssetReference  # noqa: F401
from meshassets.objects.mesh_asset.OrganMeshChoice import OrganMeshChoice  # noqa: F401

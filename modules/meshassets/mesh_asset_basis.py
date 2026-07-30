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

  simulate      may we USE the mesh in our own sim/render?
  redistribute  may we SHIP it inside a Polari release or an
                exported scene someone else receives?

CC0/public-domain clears both. CC-BY clears both WITH attribution
that must travel. CC-BY-SA and LGPL clear simulation but make
redistribution carry obligations onto whatever they touch, so those
default to reference-only until a human decides. UNVERIFIED clears
NOTHING — that is the PlantMap3D case, and an asset row in that
state refuses by name rather than sitting in a catalog looking
usable.

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

@consumers meshassets.mesh_fit, meshassets.mesh_asset_api,
           plant_morphology (organ candidates), gears (references)
"""

from objectTreeDecorators import treeObject, treeObjectInit

#: What a licence lets us do. Ordered weakest -> strongest.
LICENSE_GRADES = ('unverified', 'reference-only', 'simulate-only',
                  'simulate-and-attribute', 'unrestricted')

#: SPDX (or 'public-domain') -> the grade we treat it as. Anything
#: absent from this map is UNVERIFIED by construction: a licence we
#: have not thought about is not a licence we may rely on.
LICENSE_GRADE_BY_SPDX = {
    'CC0-1.0': 'unrestricted',
    'public-domain': 'unrestricted',
    'MIT': 'simulate-and-attribute',
    'BSD-3-Clause': 'simulate-and-attribute',
    'Apache-2.0': 'simulate-and-attribute',
    'CC-BY-4.0': 'simulate-and-attribute',
    'CC-BY-3.0': 'simulate-and-attribute',
    # Copyleft: fine to LEARN from and to run locally; shipping a
    # derivative carries obligations onto what it touches, so a
    # human decides per case rather than a catalog assuming.
    'CC-BY-SA-4.0': 'reference-only',
    'LGPL-2.1': 'reference-only',
    'GPL-3.0': 'reference-only',
    # Explicitly named so the PlantMap3D case has a row shape:
    'NONE': 'unverified',
    'NOASSERTION': 'unverified',
}

#: How the licence was established. 'api' = the hosting API's own
#: field; 'file' = a LICENSE file read; 'header' = a statement in
#: the source/asset header; 'site-terms' = the publisher's terms
#: page. The PlantMap3D lesson: check MORE THAN ONE where possible,
#: because an API can miss a header and a header can miss a file.
VERIFICATION_METHODS = ('api', 'file', 'header', 'site-terms',
                        'not-checked')

#: What the asset depicts, in OUR vocabulary — deliberately the
#: plant_morphology ORGAN_TYPES plus the mechanical kinds, so a
#: pick-and-choose query is a plain filter.
ASSET_SUBJECTS = ('leaf', 'stem', 'branch', 'root-visible', 'fruit',
                  'flower', 'tuber', 'whole-plant',
                  'gear', 'hardware', 'other')


class MeshAssetSource(treeObject):
    """A PUBLISHER of assets (a site, a repo, a pack) plus the
    licence finding for it — established once, cited by every asset
    row beneath it."""

    @treeObjectInit
    def __init__(self, name='', display_name='', url='',
                 license_spdx='NONE', license_statement='',
                 verification_method='not-checked',
                 verified_at='', approximation_valid=True,
                 formats_json='[]', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.url = url
        #: SPDX id, or 'public-domain', or 'NONE' when the publisher
        #: declares nothing (which is a FINDING, not a blank).
        self.license_spdx = license_spdx
        #: The publisher's own words, quoted. A paraphrase is how
        #: "open source" ends up meaning nothing.
        self.license_statement = license_statement
        self.verification_method = (
            verification_method
            if verification_method in VERIFICATION_METHODS
            else 'not-checked')
        self.verified_at = verified_at
        #: FALSE for subjects where "close enough" is WRONG — gears
        #: being the case in hand: an approximate gear does not
        #: mesh. Reports refuse to offer such assets as stand-ins.
        self.approximation_valid = approximation_valid
        self.formats_json = formats_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class MeshAssetReference(treeObject):
    """ONE catalogued asset. Rows carry a POINTER and a measured
    bounding box — never the mesh bytes: we do not vendor third-
    party geometry into this repo, we record where it is, what it
    is, and how well it fits."""

    @treeObjectInit
    def __init__(self, name='', display_name='', source_ref='',
                 subject='leaf', asset_url='',
                 bbox_mm_json='[]', poly_count=0,
                 morphology_note='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.source_ref = source_ref
        self.subject = (subject if subject in ASSET_SUBJECTS
                        else 'other')
        self.asset_url = asset_url
        #: [length, width, thickness] in mm AS PUBLISHED/measured —
        #: the three numbers mesh_fit compares against an
        #: OrganModel's own vector dimensions. Empty = unmeasured,
        #: and fitting REFUSES rather than guessing a size.
        self.bbox_mm_json = bbox_mm_json
        self.poly_count = poly_count
        #: What morphology this shape actually reads as, honestly
        #: (a game-asset leaf is a stylized blade, not a species).
        self.morphology_note = morphology_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class OrganMeshChoice(treeObject):
    """THE PICK: this OrganModel is approximated by that asset, at
    these per-axis scales. Created by a human choosing from the
    fit report — never auto-assigned, because "close enough" is a
    judgement and the number only informs it."""

    @treeObjectInit
    def __init__(self, name='', organ_model_ref='', asset_ref='',
                 scale_length=1.0, scale_width=1.0,
                 scale_thickness=1.0, rotation_deg_json='[0,0,0]',
                 accepted_by='', accepted_note='', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.organ_model_ref = organ_model_ref
        self.asset_ref = asset_ref
        #: Per-axis scale applied to the asset to reach the organ's
        #: vector dimensions. Equal scales = the proportions already
        #: matched; wildly unequal = the mesh is being squashed into
        #: a shape it is not, and fidelity reports how much.
        self.scale_length = scale_length
        self.scale_width = scale_width
        self.scale_thickness = scale_thickness
        self.rotation_deg_json = rotation_deg_json
        #: Who accepted this approximation, and why they judged it
        #: close enough. Blank = proposed, not accepted.
        self.accepted_by = accepted_by
        self.accepted_note = accepted_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes

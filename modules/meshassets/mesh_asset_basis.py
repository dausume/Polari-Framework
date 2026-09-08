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

from objectTreeDecorators import treeObject, treeObjectInit

#: OUR licence — the fact everything else is judged RELATIVE to.
#: Verified by the same method we apply to strangers: read the file.
#: `./LICENSE` at the suite root and in polari-framework is the full
#: GNU GPL v3 text (674 lines).
#:
#: This is the correction Dustin made on 2026-07-30, and it matters:
#: an earlier pass graded CC-BY-SA and LGPL "reference-only" as
#: though copyleft were a problem. For a GPLv3 project it is not —
#: copyleft assets are COMPATIBLE, and treating them as blocked
#: throws away usable work for no reason. Compatibility is a
#: RELATION between two licences, never a property of one.
PROJECT_LICENSE_SPDX = 'GPL-3.0-or-later'
PROJECT_LICENSE_VERIFIED_FROM = (
    './LICENSE (suite root) and polari-rf-node/polari-framework/'
    'LICENSE — GNU GPL v3 full text, read 2026-07-30')

#: How a licence relates to OURS. Each entry states whether we may
#: use the asset, what obligations TRAVEL with it, and why — the
#: "why" being the part that stops this table from becoming folklore.
#:
#: Anything absent is UNUSABLE by construction: a licence nobody has
#: reasoned about is not one to rely on, and no licence at all
#: (PlantMap3D) means default copyright, which our own licence
#: cannot fix.
COMPATIBILITY = {
    'CC0-1.0': {
        'compatible': True, 'relation': 'public-domain',
        'attribution_required': False, 'share_alike': False,
        'why': 'CC0 waives rights worldwide — nothing to satisfy. '
               'Credit is appreciated by the publishers and we give '
               'it anyway, but it is courtesy, not obligation.'},
    'public-domain': {
        'compatible': True, 'relation': 'public-domain',
        'attribution_required': False, 'share_alike': False,
        'why': 'No rights reserved; no obligations attach.'},
    'MIT': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'Permissive and GPL-compatible; the copyright notice '
               'and licence text must be preserved in what we '
               'ship.'},
    'BSD-3-Clause': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'Permissive and GPL-compatible; notice preserved.'},
    'Apache-2.0': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'GPLv3-compatible specifically (NOT GPLv2 — the '
               'patent-termination clause is why). We are v3, so '
               'this is fine.'},
    'CC-BY-4.0': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'Attribution only. The credit must travel with the '
               'asset wherever it goes.'},
    'CC-BY-3.0': {
        'compatible': True, 'relation': 'permissive',
        'attribution_required': True, 'share_alike': False,
        'why': 'Attribution only.'},
    'CC-BY-SA-4.0': {
        'compatible': True, 'relation': 'one-way-into-gplv3',
        'attribution_required': True, 'share_alike': True,
        'why': 'Creative Commons declared CC BY-SA 4.0 ONE-WAY '
               'compatible with GPLv3 (2015): BY-SA material may be '
               'adapted and released under GPLv3. ONE-WAY means we '
               'can bring it in and cannot push the result back '
               'out as BY-SA — which suits us, since we are GPLv3 '
               'already.'},
    'LGPL-2.1': {
        'compatible': True, 'relation': 'relicensable-to-gpl',
        'attribution_required': True, 'share_alike': True,
        'why': 'LGPL-2.1 section 3 lets a recipient apply the '
               'ordinary GPL "version 2 or any later version" to a '
               'copy — so it reaches GPLv3 and sits comfortably in '
               'a GPLv3 project.'},
    'GPL-3.0': {
        'compatible': True, 'relation': 'same-licence',
        'attribution_required': True, 'share_alike': True,
        'why': 'Identical terms to ours.'},
    'GPL-2.0-only': {
        'compatible': False, 'relation': 'incompatible',
        'attribution_required': True, 'share_alike': True,
        'why': 'GPLv2 WITHOUT "or later" cannot be combined with '
               'GPLv3 — the one genuinely blocking copyleft case, '
               'named so it is not confused with the compatible '
               'ones above.'},
    'NONE': {
        'compatible': False, 'relation': 'no-licence',
        'attribution_required': False, 'share_alike': False,
        'why': 'No licence means default copyright: no rights are '
               'granted to us. Our own licence cannot create '
               'permission the author never gave. Ask them.'},
    'NOASSERTION': {
        'compatible': False, 'relation': 'no-licence',
        'attribution_required': False, 'share_alike': False,
        'why': 'The host could not identify a licence — treat as '
               'unlicensed until a human reads the actual terms.'},
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
                 author='', license_spdx='NONE',
                 license_url='', license_statement='',
                 verification_method='not-checked',
                 verified_at='', approximation_valid=True,
                 formats_json='[]', is_prior=True,
                 provenance_id='', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.url = url
        #: The CREDITED author — the 'A' of the TASL attribution
        #: (Title, Author, Source, Licence) that CC asks for. Blank
        #: where a licence needs attribution is a GAP the citation
        #: record REPORTS rather than papering over with the site
        #: name.
        self.author = author
        #: Canonical licence deed/text URL, so a citation can link
        #: the terms rather than just naming them.
        self.license_url = license_url
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

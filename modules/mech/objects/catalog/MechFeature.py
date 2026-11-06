"""
@module mech.objects.catalog.MechFeature

Row class MechFeature of the mech module — one class per file (design §7).
mxc-1 (MECH_FREECAD_INTERCHANGE_PLAN §3.2: the foothold of a part; §9.1: NEW
in mech — nothing in the repo had key/role matching). The class docstring
below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class MechFeature(treeObject):
    """ONE PLACE ON A PART WHERE SOMETHING CAN LAND: a thread, a slot, a
    bore, a face, a grid cell. Compatibility is a LOOKUP, not code per
    family: two features pair when `key` matches and the roles pair
    (custom/compatibility.ROLE_PAIRS), and a joint's DOF must lie inside
    the intersection of both features' dof_free. The electronics parallel
    is a BoardFoothold."""

    @treeObjectInit
    def __init__(self, name='', variant_ref='', kind='face', key='',
                 role='plane', origin_json='[0, 0, 0]',
                 axis_json='[0, 0, 1]', extent_mm=-1.0, dims_json='{}',
                 dof_free_json='[]', load_rating_json='{}',
                 basis='undetermined', is_prior=True, provenance_id='',
                 notes='', manager=None):
        #: '<variant>:<feature>' e.g. 'iso4762-M5x10:thread',
        #: 'extrusion-2020-L300:slot:+x', 'gridfinity-bin-2x2x6:cell:0,1'.
        self.name = name
        #: MechPartVariant name.
        self.variant_ref = variant_ref
        #: catalog._shared.FEATURE_KINDS.
        self.kind = kind
        #: The compatibility key — the thing that must MATCH on the other
        #: side: 'M5x0.8' | 'slot-B6/20' | 'grid-42' | 'plane' |
        #: 'bore-8H7' | 'rail-MGN9' | 'magnet-6.5x2' | 'counterbore-M3' |
        #: 'GT2-6' | 'Tr8x2' | 'slide-45-ball'.
        self.key = key
        #: catalog._shared.FEATURE_ROLES.
        self.role = role
        #: [x, y, z] mm in the part frame (variant origin = the part's
        #: datum: a screw's head underside on its axis; a profile's end
        #: face centre; a bin's bottom corner cell centre).
        self.origin_json = origin_json
        #: [dx, dy, dz] unit direction of the feature's own axis.
        self.axis_json = axis_json
        #: Length along the axis the feature extends: thread length,
        #: slot length (= cut length), bore depth; -1 = not applicable.
        self.extent_mm = extent_mm
        #: What the MATE needs: {'pitch', 'engagement_available_mm'} for a
        #: thread; {'opening', 'depth', 'inner_width'} for a slot; {'d',
        #: 'tolerance'} for a bore; {'normal', 'area_mm2'} for a face.
        self.dims_json = dims_json
        #: Which of tx ty tz rx ry rz the feature itself leaves free
        #: (a slot: tx along it; a bore: tz + rz; a face: tx ty rz).
        self.dof_free_json = dof_free_json
        #: {'axial_n', 'shear_n', 'moment_nm', 'basis'} — -1 = undetermined.
        #: A T-nut's slip load, a slide's dynamic rating.
        self.load_rating_json = load_rating_json
        #: catalog._shared.BASES — cited | derived | knob — and from what
        #: (the notes say).
        self.basis = basis
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes

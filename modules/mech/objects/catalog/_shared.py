"""@module mech.objects.catalog._shared — what the catalogue row classes share (vocabularies); mxc-1 (MECH_FREECAD_INTERCHANGE_PLAN §3.1, §3.2; MECH_KIT_PARTS_CATALOGUE §2, §3)."""

#: MechFeature.kind — the GEOMETRIC nature of a foothold (plan §3.2 list,
#: plus the two the Gridfinity base needs: a magnet pocket and a screw
#: counterbore).
FEATURE_KINDS = ('thread', 'slot', 'bore', 'shaft', 'face', 'hole_pattern',
                 'grid_cell', 'belt_tooth', 'rail', 'pocket', 'lip',
                 'magnet', 'counterbore')

#: MechFeature.role — which SIDE of a pairing the feature is. Pairings are
#: data in custom/compatibility.ROLE_PAIRS, never code per family.
FEATURE_ROLES = ('male', 'female', 'channel', 'rider', 'plane', 'cell',
                 'socket')

#: MechPartFamily.category — the kit's coarse grouping (mxc-1 naming
#: contract; finer standards-level grouping lives on `standard`).
CATEGORIES = ('fastener', 'frame', 'motion', 'bearing', 'transmission',
              'storage', 'panel', 'hardware')

#: The shared variant-axis vocabulary (MECH_KIT_PARTS_CATALOGUE §2). A
#: family's variant_axes_json lists which of these it uses; every value a
#: variant carries is keyed by one of them.
VARIANT_AXES = ('standard', 'thread', 'pitch_series', 'nominal_length',
                'cut_length', 'head_form', 'drive', 'point_form',
                'thread_extent', 'profile_series', 'slot_type',
                'cross_section', 'open_faces', 'weight_class', 'insertion',
                'seal', 'flange', 'bore', 'od', 'width', 'teeth',
                'tooth_profile', 'belt_width', 'lead', 'starts',
                'carriage_length', 'gender', 'handedness', 'hole_count',
                'bearing_code', 'grid_x', 'grid_y', 'height_u', 'series')

#: How a number was arrived at — on dims, masses, load ratings.
BASES = ('cited', 'derived', 'measured', 'knob', 'undetermined')

#: MechPartFamily.length_rule_json['kind'].
LENGTH_RULE_KINDS = ('none', 'stepped', 'continuous')

#: The six rigid-body axes a feature can leave free — the same tuple as
#: composition.objects.interface._shared.DOF_AXES (kept literal here so
#: the catalogue imports nothing from composition at row-definition time).
DOF_AXES = ('tx', 'ty', 'tz', 'rx', 'ry', 'rz')

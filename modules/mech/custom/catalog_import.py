"""
@module mech.custom.catalog_import

mxc-1: THE CATALOGUE IMPORTER. Reads the verbatim upstream tables kept
under custom/upstream/<source>/ (each with its SOURCE.json + licence)
and turns them into the seed dicts of mech_catalog_seed.py:

  FreeCAD Fasteners WB  FsData/*def.csv   -> ISO 4762 / 7380-1 / 10642 /
      (GPL-2.0, data read, no code run)      4026 / 4032 / 4035 / 7089 /
                                             7093 / DIN 508 families, with
                                             the *length series and the
                                             *range (per-size min/max)
                                             sections of the same file
  NopSCADlib            vitamins/*.scad    -> extrusions, brackets, T-nuts,
      (GPL-3.0, tuples read by regex)         ball bearings, LM bushings,
                                             MGN rails + carriages, GT2
                                             belts + pulleys, TR8 lead
  gridfinity-rebuilt    src/core/standard.scad -> the Gridfinity constants
      (MIT)                                     (42 / 7 / 41.5 / profiles /
                                                magnet / screw)
  hand-entered (this file, cited)          -> drawer-slide (plan mxc-1 row,
                                             rated load = knob), rod
                                             (hardened shaft 6/8/10/12),
                                             TR8x4 (2-start), bore-8 GT2
                                             pulleys, Gridfinity lid, 625.

STDLIB ONLY and self-contained on purpose: it is run as
    python3 -I custom/catalog_import.py --write
from modules/mech/ (isolated mode: nothing from the upstream directories
can be imported by accident; the .scad / .csv files are parsed as TEXT,
never executed). `--write` regenerates mech_catalog_seed.py as Python
literals with a header naming the source shas; without it the importer
prints the counts and exits.

Frame conventions resolved into every feature (plan §3.2 frame_json):
  the part's long axis is +z; a screw's datum is the centre of its head
  underside with the shank along -z; a profile / rod / rail / belt runs
  from z=0 to z=L; a bin's datum is the centre of its (0,0) grid cell at
  the bottom face; a nut / washer / bearing is centred with +z through
  its axis.

@consumers mech.mech_catalog_seed (generated), mech.mech_catalog_selftest
"""
import csv
import ast
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MECH_DIR = os.path.dirname(HERE)
UPSTREAM = os.path.join(HERE, 'upstream')
PROV = 'mxc-1'
FETCHED = '2026-11-03'

FS_DIR = 'fasteners-wb-fddd07a'
NOP_DIR = 'nopscadlib-00ec289'
GF_DIR = 'gridfinity-rebuilt-910e22d'

FS_COMMIT = 'fddd07af422b7d3a69098b32333711c5eeae184c'
NOP_COMMIT = '00ec2898c0a2cdebd446f0175671b633d5ae7d5f'
GF_COMMIT = '910e22d8607fd7f5f51ad5e5cbc5287a76810bfd'

FS_LICENCE = {
    'license_spdx': 'GPL-2.0-only',
    'license_url': 'custom/upstream/%s/LICENSE' % FS_DIR,
    'license_statement': 'LICENSE: "GNU GENERAL PUBLIC LICENSE Version 2, '
                         'June 1991" (no or-later clause in the file). The '
                         'CSV values transcribe public ISO/DIN tables; read '
                         'as DATA by this importer, no workbench code run.',
    'verification_method': 'file',
}
NOP_LICENCE = {
    'license_spdx': 'GPL-3.0-or-later',
    'license_url': 'custom/upstream/%s/COPYING' % NOP_DIR,
    'license_statement': 'Every .scad header: "NopSCADlib is free software: '
                         'you can redistribute it and/or modify it under the '
                         'terms of the GNU General Public License as published '
                         'by the Free Software Foundation, either version 3 of '
                         'the License, or (at your option) any later version."',
    'verification_method': 'header',
}
GF_LICENCE = {
    'license_spdx': 'MIT',
    'license_url': 'custom/upstream/%s/LICENSE' % GF_DIR,
    'license_statement': 'LICENSE: "MIT License  Copyright (c) 2023 Kenneth '
                         'Hodson". The Gridfinity spec page '
                         '(gridfinity.xyz/specification) names no licence '
                         '(D-mxc-1): geometry is taken from this MIT source '
                         'and the spec is cited.',
    'verification_method': 'file',
}
HAND_LICENCE = {
    'license_spdx': 'GPL-3.0-or-later',
    'license_url': 'LICENSE (suite root)',
    'license_statement': 'Hand-entered in modules/mech/custom/catalog_import.py '
                         'citing AI-Notes/plans/MECH_FREECAD_INTERCHANGE_PLAN.md '
                         '§4 (row mxc-1) and MECH_KIT_PARTS_CATALOGUE.md §3.1; '
                         'the suite\'s own licence.',
    'verification_method': 'file',
}

# Thread sizes that become VARIANTS (the mxc-1 scope). Bracketed sizes
# in the WB tables, "(M3.5)", are the standard's non-preferred sizes and
# are kept in the dimension table flagged preferred=0, never as variants.
VARIANT_THREADS = ('M2', 'M2.5', 'M3', 'M4', 'M5', 'M6', 'M8')

# materials_registry ids (collab/mech-parts/data/part_material_roles.json,
# 2026-11-03) per family — stored as strings; the rows are another agent's.
MATERIALS = {
    'screw': (['steel_carbon', 'black_oxide', 'stainless_a2_a4'],
              ['steel_carbon', 'zinc_trivalent', 'pa66'],
              ['zinc_hexavalent', 'cadmium_plating']),
    'nut': (['steel_carbon', 'zinc_trivalent', 'stainless_a2_a4'],
            ['pa66', 'brass_lead_free'],
            ['zinc_hexavalent', 'brass_leaded']),
    'washer': (['steel_carbon', 'zinc_trivalent', 'stainless_a2_a4'],
               ['pa66'], ['zinc_hexavalent']),
    'tnut': (['steel_carbon', 'zinc_trivalent'],
             ['stainless_a2_a4', 'petg'],
             ['zinc_hexavalent', 'cadmium_plating']),
    'extrusion': (['al_6063'], ['al_6061'], []),
    'bracket': (['al_diecast'], ['zinc_alloy'], []),
    'bearing': (['steel_carbon'], ['stainless_a2_a4', 'aem'], ['nbr_hnbr']),
    'bushing': (['steel_carbon', 'pa66'], [], ['pom']),
    'rail': (['steel_carbon', 'stainless_a2_a4'], [], ['nbr_hnbr']),
    'rod': (['steel_carbon', 'nitriding', 'stainless_a2_a4'], [],
            ['hard_chrome']),
    'leadscrew': (['stainless_a2_a4'], [], []),
    'belt': (['tpu_mdi', 'steel_cord', 'glass_fibre_cord'],
             ['tpc_et', 'epdm_peroxide', 'aramid_cord'], ['neoprene_cr']),
    'pulley': (['al_6061'], ['pa66', 'petg'], ['pom']),
    'printed': (['petg', 'pla'], ['pa66', 'pp'], ['abs']),
    'slide': (['steel_carbon', 'zinc_trivalent'], ['stainless_a2_a4'],
              ['zinc_hexavalent']),
}

# ISO 262 coarse pitches (also read from iso262def.csv; this is the
# fallback the key builder uses when a table lacks P, e.g. washers).
COARSE_PITCH = {'M1.6': 0.35, 'M2': 0.4, 'M2.5': 0.45, 'M3': 0.5,
                'M3.5': 0.6, 'M4': 0.7, 'M5': 0.8, 'M6': 1.0, 'M8': 1.25,
                'M10': 1.5, 'M12': 1.75, 'M14': 2.0, 'M16': 2.0,
                'M20': 2.5, 'M24': 3.0}


def _j(obj):
    return json.dumps(obj, separators=(', ', ': '), sort_keys=False)


def _num(x):
    """Numbers as the leanest literal (5.0 -> 5, 4.7 stays)."""
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def thread_key(size, pitch=None):
    """'M5' (+0.8) -> 'M5x0.8' — the compatibility key of a metric
    coarse thread (naming contract §3.2)."""
    size = size.strip('()')
    p = pitch if pitch is not None else COARSE_PITCH[size]
    return '%sx%s' % (size, _num(float(p)))


def _sha(path):
    b = open(path, 'rb').read()
    return hashlib.sha256(b).hexdigest(), len(b)


# --------------------------------------------------------------------
# 1. FreeCAD Fasteners WB CSV: one file, several named sections
# --------------------------------------------------------------------

def parse_fs_csv(path):
    """A FsData CSV is a sequence of sections: one or more lines holding
    a single quoted section name (aliases: "ISO7380-1range" then
    "ISO7380-2range" name the same table), a header row, data rows,
    blank line. Returns {section: {'header': [...], 'rows': [[...]]}}."""
    out = {}
    pending = []
    header = None
    rows = None
    with open(path, newline='', encoding='utf-8') as f:
        for rec in csv.reader(f):
            if not rec or all(c.strip() == '' for c in rec):
                header = None
                rows = None
                continue
            if len(rec) == 1 and header is None:
                pending.append(rec[0])
                continue
            if header is None:
                header = rec
                rows = []
                for name in pending:
                    out[name] = {'header': header, 'rows': rows}
                pending = []
                continue
            rows.append(rec)
    return out


def _table_by_size(section):
    """A def section -> {size: {dim: number, 'preferred': 1|0}}."""
    hdr = section['header']
    table = {}
    for row in section['rows']:
        raw = row[0]
        size = raw.strip('()')
        d = {}
        for k, v in zip(hdr[1:], row[1:]):
            try:
                d[k] = _num(float(v))
            except ValueError:
                d[k] = -1
        d['preferred'] = 0 if raw.startswith('(') else 1
        table[size] = d
    return table


def _length_series(section):
    return [_num(float(r[0])) for r in section['rows']]


def _range_table(section):
    out = {}
    for r in section['rows']:
        out[r[0].strip('()')] = [_num(float(r[1])), _num(float(r[2]))]
    return out


def _source_row(name, dirname, relpath, commit, licence, project_url,
                rows_imported, rejected, notes=''):
    full = os.path.join(UPSTREAM, dirname, relpath)
    sha, nbytes = _sha(full)
    row = {
        'name': name,
        'display_name': '%s / %s' % (dirname, relpath),
        'url': '%s/blob/%s/%s' % (project_url, commit, relpath),
        'commit': commit,
        'path': 'custom/upstream/%s/%s' % (dirname, relpath),
        'sha256': sha, 'bytes': nbytes, 'fetched': FETCHED,
        'rows_imported': rows_imported,
        'rows_rejected_json': _j(rejected),
        'is_prior': True, 'provenance_id': PROV, 'notes': notes,
    }
    row.update(licence)
    return row


FS_URL = 'https://github.com/shaise/FreeCAD_FastenersWB'
NOP_URL = 'https://github.com/nophead/NopSCADlib'
GF_URL = 'https://github.com/kennetek/gridfinity-rebuilt-openscad'


def _family(name, display, category, archetype, standard, axes, size_rule,
            table, length_rule, interfaces, source_ref, mats, notes='',
            standard_url=''):
    d, a, l = MATERIALS[mats]
    return {
        'name': name, 'display_name': display, 'category': category,
        'archetype_ref': archetype, 'standard': standard,
        'standard_url': standard_url,
        'variant_axes_json': _j(axes), 'size_key_rule': size_rule,
        'dimension_table_json': _j(table),
        'length_rule_json': _j(length_rule),
        'interfaces_json': _j(interfaces),
        'generator': '', 'generator_version': '',
        'dimension_source_ref': source_ref,
        'material_default_ids_json': _j(d),
        'material_alternative_ids_json': _j(a),
        'material_legacy_ids_json': _j(l),
        'is_prior': True, 'provenance_id': PROV, 'notes': notes,
    }


def _variant(name, family, size_key, designation, axes, dims, length,
             features, notes=''):
    return {
        'name': name, 'family_ref': family, 'size_key': size_key,
        'designation': designation, 'axis_values_json': _j(axes),
        'dims_json': _j(dims), 'length_mm': _num(float(length)),
        'mass_g': -1, 'mass_g_basis': 'undetermined',
        'interfaces_json': _j([f['name'] for f in features]),
        'item_ref': '', 'is_prior': True, 'provenance_id': PROV,
        'notes': notes,
    }


def _feature(variant, tag, kind, key, role, origin=(0, 0, 0), axis=(0, 0, 1),
             extent=-1, dims=None, dof=(), load=None, basis='cited',
             notes=''):
    return {
        'name': '%s:%s' % (variant, tag), 'variant_ref': variant,
        'kind': kind, 'key': key, 'role': role,
        'origin_json': _j([_num(float(c)) for c in origin]),
        'axis_json': _j(list(axis)), 'extent_mm': _num(float(extent)),
        'dims_json': _j(dims or {}), 'dof_free_json': _j(list(dof)),
        'load_rating_json': _j(load or {}),
        'basis': basis, 'is_prior': True, 'provenance_id': PROV,
        'notes': notes,
    }


def _plane(variant, tag, origin, axis, dims=None, notes=''):
    return _feature(variant, tag, 'face', 'plane', 'plane', origin, axis,
                    dims=dims, dof=('tx', 'ty', 'rz'), basis='derived',
                    notes=notes)


class Bundle:
    """Accumulates the four seed lists."""

    def __init__(self):
        self.sources, self.families, self.variants, self.features = [], [], [], []

    def add(self, variant, features):
        self.variants.append(variant)
        self.features.extend(features)


# ---- screws ----------------------------------------------------------

SCREW_FAMILIES = [
    # family, csv, def-section, length-section, range-section, standard, display, head_form
    ('iso4762', 'iso4762def.csv', 'ISO4762def', 'ISO4762length',
     'ISO4762range', 'ISO 4762', 'Hexagon socket head cap screw', 'cap'),
    ('iso7380-1', 'iso7380def.csv', 'ISO7380-1def', 'ISO7380-1length',
     'ISO7380-1range', 'ISO 7380-1', 'Hexagon socket button head screw',
     'button'),
    ('iso10642', 'iso10642def.csv', 'ISO10642def', 'ISO10642length',
     'ISO10642range', 'ISO 10642', 'Hexagon socket countersunk head screw',
     'countersunk'),
    ('iso4026', 'iso4026def.csv', 'ISO4026def', 'ISO4026length',
     'ISO4026range', 'ISO 4026', 'Hexagon socket set screw, flat point',
     'none'),
]


def _screw_dims(fam, row):
    """Head dims by the standard's own names; -1 where the family has
    none (a set screw has no head)."""
    dk = row.get('dk_max', row.get('dk', row.get('dk_theo', -1)))
    k = row.get('k', row.get('csh_height', -1))
    return dk, k


def import_screws(b):
    for fam, csvf, dsec, lsec, rsec, std, display, head in SCREW_FAMILIES:
        secs = parse_fs_csv(os.path.join(UPSTREAM, FS_DIR, 'FsData', csvf))
        table = _table_by_size(secs[dsec])
        series = _length_series(secs[lsec])
        rng = _range_table(secs[rsec])
        src = 'fasteners-wb:%s' % csvf
        rejected = [{'row': s, 'why': 'above M8: table kept, no variant'}
                    for s in table if s not in VARIANT_THREADS]
        b.sources.append(_source_row(
            src, FS_DIR, 'FsData/%s' % csvf, FS_COMMIT, FS_LICENCE, FS_URL,
            len(table), rejected,
            notes='sections read: %s (dims), %s (nominal length series), '
                  '%s (per-size min/max length)' % (dsec, lsec, rsec)))
        axes = ['standard', 'thread', 'nominal_length', 'head_form',
                'drive', 'thread_extent'] + (['point_form'] if head == 'none' else [])
        tmpl = [
            {'kind': 'thread', 'key': 'M{thread}x{P}', 'role': 'male',
             'count': 1, 'dims': ['P', 'b', 'd'], 'dof_free': ['rz'],
             'origin_rule': 'head underside centre, shank along -z',
             'notes': 'extent = min(L, b): thread length b for long screws, '
                      'full length below it'},
        ] + ([] if head == 'none' else [
            {'kind': 'face', 'key': 'plane', 'role': 'plane', 'count': 1,
             'dims': ['dk', 'k'], 'dof_free': ['tx', 'ty', 'rz'],
             'origin_rule': 'head underside (the clamped face)'},
        ])
        b.families.append(_family(
            fam, '%s %s' % (std, display), 'fastener', 'at-screw', std, axes,
            '<thread>x<nominal_length>', table,
            {'kind': 'stepped', 'series': series, 'per_size': rng},
            tmpl, src, 'screw',
            notes='head_form=%s; drive=hex socket; variants M2-M8 only, '
                  'every nominal length of the series inside the range '
                  'table; -1 = the table gives no value' % head))
        for size in VARIANT_THREADS:
            if size not in table or size not in rng:
                continue
            row = table[size]
            lo, hi = rng[size]
            P = row['P']
            key = thread_key(size, P)
            d = float(size[1:])
            dk, k = _screw_dims(fam, row)
            for L in series:
                if L < lo or L > hi:
                    continue
                vname = '%s-%sx%s' % (fam, size, L)
                dims = dict(row)
                dims.pop('preferred', None)
                dims['d'] = _num(d)
                dims['L'] = L
                bt = row.get('b', -1)
                thread_len = L if (bt == -1 or L <= bt) else bt
                feats = [_feature(
                    vname, 'thread', 'thread', key, 'male', (0, 0, 0),
                    (0, 0, -1), thread_len,
                    {'pitch': P, 'd': _num(d), 'thread_length': _num(thread_len),
                     'L': L}, ('rz',),
                    notes='helical: tz is coupled to rz by the pitch')]
                if head != 'none':
                    feats.append(_plane(
                        vname, 'head-seat', (0, 0, 0), (0, 0, -1),
                        {'dk': dk, 'k': k, 'normal_z': -1}))
                b.add(_variant(vname, fam, size, '%s %sx%s' % (std, size, L),
                               {'standard': std, 'thread': size,
                                'nominal_length': L, 'head_form': head,
                                'drive': 'hex socket',
                                'thread_extent': 'full' if thread_len == L else 'partial'},
                               dims, L, feats), feats)


# ---- nuts ------------------------------------------------------------

NUT_FAMILIES = [
    ('iso4032', 'iso4032def.csv', 'ISO4032def', 'ISO 4032',
     'Hexagon regular nut, style 1', 'hex'),
    ('iso4035', 'iso4035def.csv', 'ISO4035def', 'ISO 4035',
     'Hexagon thin nut, chamfered', 'thin_hex'),
]


def import_nuts(b):
    for fam, csvf, dsec, std, display, form in NUT_FAMILIES:
        secs = parse_fs_csv(os.path.join(UPSTREAM, FS_DIR, 'FsData', csvf))
        table = _table_by_size(secs[dsec])
        src = 'fasteners-wb:%s' % csvf
        rejected = [{'row': s, 'why': 'above M8: table kept, no variant'}
                    for s in table if s not in VARIANT_THREADS]
        b.sources.append(_source_row(src, FS_DIR, 'FsData/%s' % csvf,
                                     FS_COMMIT, FS_LICENCE, FS_URL,
                                     len(table), rejected,
                                     notes='section read: %s' % dsec))
        tmpl = [
            {'kind': 'thread', 'key': 'M{thread}x{P}', 'role': 'female',
             'count': 1, 'dims': ['P', 'm', 's_nom', 'e'],
             'dof_free': ['rz'],
             'origin_rule': 'nut centre, bottom face at z=0, axis +z',
             'notes': 'extent = m: the engagement this nut offers'},
            {'kind': 'face', 'key': 'plane', 'role': 'plane', 'count': 2,
             'dims': ['dw'], 'dof_free': ['tx', 'ty', 'rz'],
             'origin_rule': 'bottom face (normal -z) and top face (+z)'},
        ]
        b.families.append(_family(
            fam, '%s %s' % (std, display), 'fastener', 'at-nut', std,
            ['standard', 'thread', 'flange'], '<thread>', table,
            {'kind': 'none'}, tmpl, src, 'nut',
            notes='form=%s; s_nom = across flats, m = height, e = across '
                  'corners, dw = bearing face diameter' % form))
        for size in VARIANT_THREADS:
            if size not in table:
                continue
            row = table[size]
            key = thread_key(size, row['P'])
            vname = '%s-%s' % (fam, size)
            dims = dict(row)
            dims.pop('preferred', None)
            dims['d'] = _num(float(size[1:]))
            m = row['m']
            feats = [
                _feature(vname, 'thread', 'thread', key, 'female', (0, 0, 0),
                         (0, 0, 1), m,
                         {'pitch': row['P'], 'd': dims['d'],
                          'engagement_available_mm': m}, ('rz',)),
                _plane(vname, 'face-bottom', (0, 0, 0), (0, 0, -1),
                       {'dw': row['dw'], 'normal_z': -1}),
                _plane(vname, 'face-top', (0, 0, m), (0, 0, 1),
                       {'dw': row['dw'], 'normal_z': 1}),
            ]
            b.add(_variant(vname, fam, size, '%s %s' % (std, size),
                           {'standard': std, 'thread': size, 'flange': 0},
                           dims, -1, feats), feats)


# ---- washers ---------------------------------------------------------

WASHER_FAMILIES = [
    ('iso7089', 'iso7089def.csv', 'ISO7089def', 'ISO 7089',
     'Plain washer, normal series', 'flat'),
    ('iso7093', 'iso7093def.csv', 'ISO7093-1def', 'ISO 7093-1',
     'Plain washer, large series', 'large'),
]


def import_washers(b):
    for fam, csvf, dsec, std, display, form in WASHER_FAMILIES:
        secs = parse_fs_csv(os.path.join(UPSTREAM, FS_DIR, 'FsData', csvf))
        table = _table_by_size(secs[dsec])
        src = 'fasteners-wb:%s' % csvf
        rejected = [{'row': s, 'why': 'above M8: table kept, no variant'}
                    for s in table if s not in VARIANT_THREADS]
        b.sources.append(_source_row(src, FS_DIR, 'FsData/%s' % csvf,
                                     FS_COMMIT, FS_LICENCE, FS_URL,
                                     len(table), rejected,
                                     notes='section read: %s' % dsec))
        tmpl = [
            {'kind': 'bore', 'key': 'M{thread}x{P}', 'role': 'socket',
             'count': 1, 'dims': ['d1_min', 'd2_max', 'h'],
             'dof_free': ['tz', 'rz'],
             'origin_rule': 'washer centre, bottom face at z=0',
             'notes': 'clearance bore keyed by the screw thread it passes '
                      '(socket <-> the screw\'s male)'},
            {'kind': 'face', 'key': 'plane', 'role': 'plane', 'count': 2,
             'dims': ['d2_max'], 'dof_free': ['tx', 'ty', 'rz'],
             'origin_rule': 'bottom (-z) and top (+z) faces'},
        ]
        b.families.append(_family(
            fam, '%s %s' % (std, display), 'fastener', 'at-washer', std,
            ['standard', 'thread'], '<thread>', table, {'kind': 'none'},
            tmpl, src, 'washer',
            notes='form=%s; d1 = hole, d2 = outer, h = thickness. The WB '
                  'table carries no pitch; the key uses the ISO 262 coarse '
                  'pitch of the nominal thread' % form))
        for size in VARIANT_THREADS:
            if size not in table:
                continue
            row = table[size]
            key = thread_key(size)
            vname = '%s-%s' % (fam, size)
            dims = dict(row)
            dims.pop('preferred', None)
            dims['d'] = _num(float(size[1:]))
            h = row['h']
            feats = [
                _feature(vname, 'bore', 'bore', key, 'socket', (0, 0, 0),
                         (0, 0, 1), h,
                         {'d1': row['d1_min'], 'd2': row['d2_max'], 'h': h},
                         ('tz', 'rz')),
                _plane(vname, 'face-bottom', (0, 0, 0), (0, 0, -1),
                       {'d2': row['d2_max'], 'normal_z': -1}),
                _plane(vname, 'face-top', (0, 0, h), (0, 0, 1),
                       {'d2': row['d2_max'], 'normal_z': 1}),
            ]
            b.add(_variant(vname, fam, size, '%s %s' % (std, size),
                           {'standard': std, 'thread': size},
                           dims, -1, feats), feats)


# ---- DIN 508 T-nuts (machine-tool T-slots, DIN 650) ---------------------

def import_din508(b):
    csvf = 'din508def.csv'
    secs = parse_fs_csv(os.path.join(UPSTREAM, FS_DIR, 'FsData', csvf))
    sizes = [r[0] for r in secs['DIN508def']['rows']]
    widths = [int(w.split()[0]) for w in secs['DIN508slotwidths']['header'][1:]]

    def grid(sec):
        out = {}
        for r in secs[sec]['rows']:
            out[r[0]] = [float(v) for v in r[1:]]
        return out
    sw, e, f, h, k = (grid('DIN508slotwidths'), grid('DIN508e'),
                      grid('DIN508f'), grid('DIN508h'), grid('DIN508k'))
    table = {}
    for size in sizes:
        for i, w in enumerate(widths):
            if sw[size][i] > 0:
                table['%s-%d' % (size, w)] = {
                    'slot_a': w, 'e': _num(e[size][i]), 'f': _num(f[size][i]),
                    'h': _num(h[size][i]), 'k': _num(k[size][i]),
                    'P': COARSE_PITCH.get(size, -1), 'preferred': 1}
    src = 'fasteners-wb:%s' % csvf
    rejected = [{'row': s, 'why': 'above M8: table kept, no variant'}
                for s in table if s.split('-')[0] not in VARIANT_THREADS]
    b.sources.append(_source_row(
        src, FS_DIR, 'FsData/%s' % csvf, FS_COMMIT, FS_LICENCE, FS_URL,
        len(table), rejected,
        notes='sections read: DIN508def (sizes), DIN508slotwidths (which '
              'slot widths each thread comes in), DIN508e/f/h/k (dims per '
              'thread x slot width); pitch from ISO 262 coarse'))
    tmpl = [
        {'kind': 'thread', 'key': 'M{thread}x{P}', 'role': 'female',
         'count': 1, 'dims': ['P', 'h'], 'dof_free': ['rz'],
         'origin_rule': 'nut centre, slot-side face at z=0, thread axis +z'},
        {'kind': 'slot', 'key': 'slot-DIN650-{slot_a}', 'role': 'rider',
         'count': 1, 'dims': ['slot_a', 'e', 'f', 'k'], 'dof_free': ['tx'],
         'origin_rule': 'rides a DIN 650 machine-tool T-slot of width a; '
                        'NOT an aluminium-extrusion slot (those are '
                        'slot-B6/20 etc. on tnut-sliding / tnut-hammer)'},
    ]
    b.families.append(_family(
        'din508', 'DIN 508 T-slot nut (for DIN 650 T-slots)', 'fastener',
        'at-t-nut', 'DIN 508', ['standard', 'thread', 'slot_type'],
        '<thread>-<slot_a>', table, {'kind': 'none'}, tmpl, src, 'tnut',
        notes='classic machine-tool T-nut; a = slot width, e = nut width, '
              'f = step height, h = total height, k = neck height'))
    for sk, row in table.items():
        size, w = sk.split('-')
        if size not in VARIANT_THREADS:
            continue
        key = thread_key(size, row['P'])
        vname = 'din508-%s' % sk
        dims = dict(row)
        dims.pop('preferred', None)
        dims['d'] = _num(float(size[1:]))
        feats = [
            _feature(vname, 'thread', 'thread', key, 'female', (0, 0, 0),
                     (0, 0, 1), row['h'],
                     {'pitch': row['P'], 'd': dims['d'],
                      'engagement_available_mm': row['h']}, ('rz',)),
            _feature(vname, 'slot', 'slot', 'slot-DIN650-%s' % w, 'rider',
                     (0, 0, 0), (1, 0, 0), row['e'],
                     {'slot_a': int(w), 'e': row['e'], 'f': row['f'],
                      'k': row['k']}, ('tx',)),
        ]
        b.add(_variant(vname, 'din508', sk, 'DIN 508 %s slot %s' % (size, w),
                       {'standard': 'DIN 508', 'thread': size,
                        'slot_type': 'DIN650-%s' % w},
                       dims, -1, feats), feats)


# --------------------------------------------------------------------
# 2. NopSCADlib tuples: `NAME = [ ... ];` parsed as text
# --------------------------------------------------------------------

_TUPLE_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(\[.*?\]);',
                       re.M | re.S)
_CONST_RE = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]+);', re.M)


def _split_top(s):
    """Split on commas at bracket depth 0, respecting quotes."""
    parts, depth, cur, q = [], 0, [], False
    for ch in s:
        if ch == '"':
            q = not q
        if not q:
            if ch in '[(':
                depth += 1
            elif ch in '])':
                depth -= 1
            elif ch == ',' and depth == 0:
                parts.append(''.join(cur))
                cur = []
                continue
        cur.append(ch)
    tail = ''.join(cur)
    if tail.strip():
        parts.append(tail)
    return [p.strip() for p in parts]


def _arith(expr):
    """Evaluate a pure-number arithmetic expression (19.05/2, 6.5 / 2)
    through the ast — never eval()."""
    node = ast.parse(expr, mode='eval').body

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        raise ValueError(expr)
    return ev(node)


_OPS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}


def scad_value(tok, consts=None):
    """One OpenSCAD literal -> python: "x" -> str, 12 -> number,
    true/false -> bool, [..] -> list, an identifier -> its name (a
    reference, kept as a string) or its value when `consts` knows it,
    an arithmetic expression over numbers / known constants -> number."""
    tok = tok.strip()
    if tok.startswith('"') and tok.endswith('"'):
        return tok[1:-1]
    if tok.startswith('[') and tok.endswith(']'):
        inner = tok[1:-1].strip()
        return [scad_value(p, consts) for p in _split_top(inner)] if inner else []
    if tok in ('true', 'false'):
        return tok == 'true'
    try:
        return _num(float(tok))
    except ValueError:
        pass
    if consts is not None:
        sub = re.sub(r'[A-Za-z_][A-Za-z0-9_.]*',
                     lambda m: (str(consts[m.group(0)])
                                if isinstance(consts.get(m.group(0)), (int, float))
                                else m.group(0)), tok)
        if re.fullmatch(r'[\d.\s()+\-*/]+', sub):
            try:
                return _num(_arith(sub))
            except (ValueError, SyntaxError, ZeroDivisionError):
                pass
    if re.fullmatch(r'[\d.\s()+\-*/]+', tok):
        try:
            return _num(_arith(tok))
        except (ValueError, SyntaxError, ZeroDivisionError):
            pass
    return tok


def parse_scad_tuples(path):
    """{NAME: [values]} for every `NAME = [ ... ];` in the file (comment
    lines stripped first so a '//' never hides a tuple or adds one)."""
    text = open(path, encoding='utf-8').read()
    text = re.sub(r'//[^\n]*', '', text)
    out = {}
    for m in _TUPLE_RE.finditer(text):
        out[m.group(1)] = scad_value(m.group(2))
    return out


def parse_scad_constants(path):
    """{NAME: value} for `NAME = <expr>;` lines, resolving references to
    earlier constants when the expression is arithmetic; anything else
    (a tan(), a concat()) is kept as its source text."""
    text = open(path, encoding='utf-8').read()
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    out = {}
    for m in _CONST_RE.finditer(text):
        name, expr = m.group(1), ' '.join(m.group(2).split())
        if expr.startswith('function') or expr.startswith('module'):
            continue
        out[name] = scad_value(expr, out)
    return out


def _nop_source(b, f, rows, tables, notes=''):
    src = 'nopscadlib:%s' % f
    b.sources.append(_source_row(src, NOP_DIR, 'vitamins/%s' % f, NOP_COMMIT,
                                 NOP_LICENCE, NOP_URL, rows, [],
                                 notes='tuples read: %s. %s' % (tables, notes)))
    return src


def _screw_ref_key(ref):
    """'M3_cap_screw' / 'M4_grub_screw' -> 'M3x0.5' / 'M4x0.7'."""
    m = re.match(r'M(\d+)(p(\d+))?_', ref)
    size = 'M%s' % m.group(1) + ('.%s' % m.group(3) if m.group(2) else '')
    return thread_key(size), size


# ---- extrusions --------------------------------------------------------

EXTRUSION_SIZES = ['1515', '2020', '2040', '2060', '2080', '3030', '4040', '4080']
EXTRUSION_FIELDS = ['W', 'H', 'd1', 'd2', 'sq', 'cw', 'cwi', 't', 'st', 'f',
                    'recess']
EXTRUSION_LENGTH_RULE = {'kind': 'continuous', 'min': 100, 'max': 1000,
                         'step': 100,
                         'notes': 'cut to length; seeded variants L300 and L500'}
SEED_PROFILE_LENGTHS = (300, 500)


def _tap_for(d1):
    """Centre-bore diameter -> the coarse thread whose tap drill it is
    (d - P within 0.3 mm), '' if none."""
    for size, p in COARSE_PITCH.items():
        if abs((float(size[1:]) - p) - abs(d1)) <= 0.3:
            return size
    return ''


def _slot_key(cw, W):
    return 'slot-B%d/%d' % (round(cw), W)


def import_extrusions(b):
    f = 'extrusions.scad'
    tup = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', f))
    table = {}
    for size in EXTRUSION_SIZES:
        vals = tup['E%s' % size]
        row = {k: (v if not isinstance(v, (list, bool)) else (0 if v is False else v[0]))
               for k, v in zip(EXTRUSION_FIELDS, vals[1:])}
        row['recess_depth'] = vals[11][1] if isinstance(vals[11], list) else 0
        row['series'] = row['W']
        row['cells_x'] = int(row['W'] / row['W'])
        row['cells_y'] = int(round(row['H'] / row['W']))
        row['slot_count'] = 2 * (row['cells_x'] + row['cells_y'])
        row['centre_bore_tap'] = float(_tap_for(row['d1'])[1:] or -1)
        table[size] = row
    src = _nop_source(b, f, len(table),
                      ', '.join('E%s' % s for s in EXTRUSION_SIZES),
                      'fields W H d1 d2 sq cw cwi t st f recess per the '
                      'file header; d1 = centre-bore diameter (negative in '
                      'the lib = drilled), cw = slot opening, cwi = inner '
                      'slot width, t = wall, st = slot top thickness')
    tmpl = [
        {'kind': 'slot', 'key': 'slot-B{cw}/{series}', 'role': 'channel',
         'count_rule': '2*(cells_x+cells_y)', 'dims': ['cw', 'cwi', 't', 'st'],
         'dof_free': ['tz'],
         'origin_rule': 'one per outer face cell: +x/-x faces carry cells_y '
                        'slots, +y/-y faces carry cells_x; slot runs along +z '
                        'from z=0 to z=L'},
        {'kind': 'bore', 'key': 'bore-{d1}', 'role': 'socket',
         'count_rule': 'cells_x*cells_y', 'dims': ['d1'],
         'dof_free': ['tz', 'rz'],
         'origin_rule': 'cell centre, both ends; tappable to the coarse '
                        'thread whose tap drill it is (centre_bore_tap)'},
        {'kind': 'face', 'key': 'plane', 'role': 'plane', 'count': 2,
         'dims': ['W', 'H'], 'dof_free': ['tx', 'ty', 'rz'],
         'origin_rule': 'end faces z=0 (-z) and z=L (+z)'},
    ]
    b.families.append(_family(
        'extrusion', 'Aluminium T-slot extrusion (B-type)', 'frame',
        'at-extrusion', '', ['series', 'cross_section', 'slot_type',
                             'open_faces', 'cut_length'],
        '<series><cells>-L<cut_length>', table, EXTRUSION_LENGTH_RULE, tmpl,
        src, 'extrusion',
        notes='sizes 1515 2020 2040 2060 2080 3030 4040 4080 from '
              'NopSCADlib E-tuples; all faces open (the 3/2/1-slot '
              'topologies of BOLTS/FrameForge are not seeded in mxc-1); '
              'slot key = slot-B<opening>/<series>'))
    for size, row in table.items():
        W, H, cw, series = row['W'], row['H'], row['cw'], row['series']
        key = _slot_key(cw, series)
        for L in SEED_PROFILE_LENGTHS:
            vname = 'extrusion-%s-L%d' % (size, L)
            dims = dict(row)
            dims['L'] = L
            feats = []
            sd = {'opening': cw, 'inner_width': row['cwi'], 'wall': row['t'],
                  'slot_top': row['st'], 'depth': _num(round((row['cwi'] - cw) / 2 + row['st'], 2))}
            for i in range(row['cells_y']):
                y = -H / 2 + series * (i + 0.5)
                feats.append(_feature(vname, 'slot:+x:%d' % i, 'slot', key,
                                      'channel', (W / 2, y, 0), (0, 0, 1), L,
                                      sd, ('tz',)))
                feats.append(_feature(vname, 'slot:-x:%d' % i, 'slot', key,
                                      'channel', (-W / 2, y, 0), (0, 0, 1), L,
                                      sd, ('tz',)))
            for i in range(row['cells_x']):
                x = -W / 2 + series * (i + 0.5)
                feats.append(_feature(vname, 'slot:+y:%d' % i, 'slot', key,
                                      'channel', (x, H / 2, 0), (0, 0, 1), L,
                                      sd, ('tz',)))
                feats.append(_feature(vname, 'slot:-y:%d' % i, 'slot', key,
                                      'channel', (x, -H / 2, 0), (0, 0, 1), L,
                                      sd, ('tz',)))
            n = 0
            for j in range(row['cells_y']):
                for i in range(row['cells_x']):
                    x = -W / 2 + series * (i + 0.5)
                    y = -H / 2 + series * (j + 0.5)
                    for zc, ax, tag in ((0, (0, 0, -1), 'end0'), (L, (0, 0, 1), 'endL')):
                        feats.append(_feature(
                            vname, 'bore:%d:%s' % (n, tag), 'bore',
                            'bore-%s' % _num(abs(row['d1'])), 'socket',
                            (x, y, zc), ax, L,
                            {'d': _num(abs(row['d1'])),
                             'tap': row['centre_bore_tap']}, ('tz', 'rz'),
                            notes='tap drill for M%s' % _num(row['centre_bore_tap'])
                            if row['centre_bore_tap'] > 0 else ''))
                    n += 1
            feats.append(_plane(vname, 'end:0', (0, 0, 0), (0, 0, -1),
                                {'W': W, 'H': H, 'normal_z': -1}))
            feats.append(_plane(vname, 'end:L', (0, 0, L), (0, 0, 1),
                                {'W': W, 'H': H, 'normal_z': 1}))
            b.add(_variant(vname, 'extrusion', size,
                           'T-slot %s x %d' % (size, L),
                           {'series': series,
                            'cross_section': '%dx%d' % (row['cells_x'], row['cells_y']),
                            'slot_type': 'B%d' % round(cw),
                            'open_faces': row['slot_count'],
                            'cut_length': L},
                           dims, L, feats), feats)


# ---- sliding / hammer T-nuts ----------------------------------------------

TNUT_FIELDS = ['screw', 'width', 'thickness', 'nyloc', 'washer', 'trap',
               'sx', 'ty1', 'ty2', 'hammer']


def _tnut_rows(tup):
    """{name: row} for the sliding / hammer / ball nut tuples; the M6
    sliding nut tuple has an extra numeric field (hammer-nut profile
    depth) before its `hammer` flag — the file's own irregularity."""
    rows = {}
    for name, vals in tup.items():
        if not (name.endswith('_t_nut') or name.endswith('_hammer_nut')):
            continue
        v = vals[1:]
        row = dict(zip(TNUT_FIELDS[:9], v[:9]))
        row['hammer'] = 1 if v[-1] is True else 0
        row['extra'] = v[9] if len(v) == 11 else 0
        rows[name] = row
    return rows


def _slot_series_for_width(w):
    """Nut width -> the extrusion series whose slot it rides (the
    E-tuples: cw 6 -> 20-series, cw 8 -> 30-series, cw 10 -> 40)."""
    return {6: 20, 8: 30, 10: 40}[int(round(w))]


def import_tnuts(b):
    f = 'nuts.scad'
    tup = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', f))
    rows = _tnut_rows(tup)
    src = _nop_source(b, f, len(rows),
                      ', '.join(sorted(rows)),
                      'fields screw width thickness nyloc(total height) '
                      'washer trap sx(length) ty1(width) ty2(top width) '
                      'hammer per the file comments; hex-nut tuples in the '
                      'same file are not read (ISO 4032 is the hex source)')
    specs = [
        ('tnut-sliding', 'Sliding T-nut (slide in from the profile end)',
         'slide', lambda n: n.endswith('_sliding_t_nut') or n.endswith('_sliding_ball_t_nut')),
        ('tnut-hammer', 'Hammer / roll-in T-nut (drop in, quarter turn)',
         'roll_in', lambda n: n.endswith('_hammer_nut')),
    ]
    for fam, display, insertion, pick in specs:
        table = {}
        for name, row in rows.items():
            if not pick(name):
                continue
            m = re.match(r'M(\d+)_', name)
            size = 'M%s' % m.group(1)
            slot = int(round(row['width']))
            sk = 'slot%d-%s' % (slot, size)
            table[sk] = {'d': int(m.group(1)), 'P': COARSE_PITCH[size],
                         'slot_w': slot, 'series': _slot_series_for_width(slot),
                         'thickness': row['thickness'], 'height': row['nyloc'],
                         'length': row['sx'], 'width_bottom': row['ty1'],
                         'width_top': row['ty2'], 'ball': 1 if 'ball' in name else 0,
                         'preferred': 1}
        tmpl = [
            {'kind': 'thread', 'key': 'M{thread}x{P}', 'role': 'female',
             'count': 1, 'dims': ['P', 'height'], 'dof_free': ['rz'],
             'origin_rule': 'nut centre, slot-side face z=0, thread axis +z '
                            '(out of the slot)',
             'notes': 'extent = height: the engagement the nut offers'},
            {'kind': 'slot', 'key': 'slot-B{slot_w}/{series}', 'role': 'rider',
             'count': 1, 'dims': ['slot_w', 'length', 'width_bottom'],
             'dof_free': ['tz'],
             'origin_rule': 'rides the profile slot along +z'},
        ]
        b.families.append(_family(
            fam, display, 'fastener', 'at-t-nut', '',
            ['thread', 'slot_type', 'insertion'], 'slot<slot_w>-<thread>',
            table, {'kind': 'none'}, tmpl, src, 'tnut',
            notes='insertion=%s; slot_w 6 = 20-series B6 slot, 8 = 30-series '
                  'B8; the M8 ball nut is a sliding nut with a spring ball' % insertion))
        for sk, row in table.items():
            size = 'M%d' % row['d']
            if size not in VARIANT_THREADS:
                continue
            key = thread_key(size, row['P'])
            vname = '%s-%s' % (fam, sk)
            dims = dict(row)
            dims.pop('preferred', None)
            feats = [
                _feature(vname, 'thread', 'thread', key, 'female', (0, 0, 0),
                         (0, 0, 1), row['height'],
                         {'pitch': row['P'], 'd': row['d'],
                          'engagement_available_mm': row['height']}, ('rz',),
                         load={'axial_n': -1, 'shear_n': -1, 'moment_nm': -1,
                               'basis': 'undetermined'},
                         notes='slip load in the slot: undetermined until measured'),
                _feature(vname, 'slot', 'slot',
                         _slot_key(row['slot_w'], row['series']), 'rider',
                         (0, 0, 0), (0, 0, 1), row['length'],
                         {'slot_w': row['slot_w'], 'length': row['length'],
                          'width_bottom': row['width_bottom']}, ('tz',)),
            ]
            b.add(_variant(vname, fam, sk, '%s %s slot %d' % (display.split(' (')[0], size, row['slot_w']),
                           {'thread': size, 'slot_type': 'B%d' % row['slot_w'],
                            'insertion': insertion},
                           dims, -1, feats), feats)


# ---- brackets ----------------------------------------------------------

def import_brackets(b):
    f = 'extrusion_brackets.scad'
    tup = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', f))
    ext = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', 'extrusions.scad'))
    nuts = _tnut_rows(parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', 'nuts.scad')))
    src = _nop_source(b, f, 4, 'E20/E40_inner_corner_bracket, E20/E40_corner_bracket',
                      'accessor order per extrusion_bracket.scad: inner = '
                      '[name, size[x,y,t], tnut, extrusion, screw_offsets]; '
                      'corner = [name, size, base_thickness, side_thickness, '
                      'hole_offset, tnut, extrusion]; the 3D cube brackets are '
                      'not seeded in mxc-1')

    def slot_for(ext_name, nut_name):
        e = ext[ext_name]
        W, cw = e[1], e[6]
        n = nuts[nut_name]
        return _slot_key(cw, W), W, n

    # inner corner brackets: legs ride the slots of both profiles
    table = {}
    for series, name in (('20', 'E20_inner_corner_bracket'), ('40', 'E40_inner_corner_bracket')):
        v = tup[name]
        key, W, nut = slot_for(v[3], v[2])
        tk, size = _screw_ref_key(v[2])
        table[series] = {'size_x': v[1][0], 'size_y': v[1][1], 'thickness': v[1][2],
                         'screw_offset_a': v[4][0], 'screw_offset_b': v[4][1],
                         'series': W, 'slot_w': round(ext[v[3]][6]),
                         'screw_d': float(size[1:]), 'P': COARSE_PITCH[size],
                         'hole_count': 2, 'preferred': 1}
    tmpl = [
        {'kind': 'slot', 'key': 'slot-B{slot_w}/{series}', 'role': 'rider',
         'count': 2, 'dims': ['size_x', 'thickness'], 'dof_free': ['tz'],
         'origin_rule': 'one leg in each profile slot; legs at 90 deg'},
        {'kind': 'bore', 'key': 'M{screw_d}x{P}', 'role': 'socket', 'count': 2,
         'dims': ['screw_d'], 'dof_free': ['tz', 'rz'],
         'origin_rule': 'one clearance hole per leg at screw_offset from the end'},
    ]
    b.families.append(_family(
        'bracket-inner', 'Inner corner bracket (hidden, in-slot)', 'frame',
        'at-bracket', '', ['series', 'hole_count'], '<series>', table,
        {'kind': 'none'}, tmpl, src, 'bracket',
        notes='the legs sit INSIDE the two slots and pull them together with '
              'one screw + T-nut per leg; NopSCADlib pairs the 20-series one '
              'with an M4 sliding nut (hole takes M4; M5 is the common kit size)'))
    for series, row in table.items():
        vname = 'bracket-inner-%s' % series
        key = _slot_key(row['slot_w'], row['series'])
        tk = thread_key('M%s' % _num(row['screw_d']), row['P'])
        dims = dict(row)
        dims.pop('preferred', None)
        feats = []
        for i, (ax, org) in enumerate((((0, 0, 1), (0, 0, 0)), ((1, 0, 0), (0, 0, 0)))):
            feats.append(_feature(vname, 'leg:%d' % i, 'slot', key, 'rider', org, ax,
                                  row['size_x'], {'slot_w': row['slot_w'],
                                                  'length': row['size_x'],
                                                  'thickness': row['thickness']}, ('tz',) if i == 0 else ('tx',)))
            hole = [c * row['screw_offset_a'] for c in ax]
            feats.append(_feature(vname, 'hole:%d' % i, 'bore', tk, 'socket', hole,
                                  (0, 1, 0), row['thickness'],
                                  {'d': row['screw_d'], 'depth': row['thickness']},
                                  ('tz', 'rz')))
        b.add(_variant(vname, 'bracket-inner', series,
                       'Inner corner bracket %s-series' % series,
                       {'series': row['series'], 'hole_count': 2},
                       dims, -1, feats), feats)

    # L corner brackets: two faces on the profiles, one hole each
    table = {}
    for series, name in (('20', 'E20_corner_bracket'), ('40', 'E40_corner_bracket')):
        v = tup[name]
        tk, size = _screw_ref_key(v[5])
        table[series] = {'size_x': v[1][0], 'size_y': v[1][1], 'size_z': v[1][2],
                         'base_thickness': v[2], 'side_thickness': v[3],
                         'hole_offset': v[4], 'series': ext[v[6]][1],
                         'screw_d': float(size[1:]), 'P': COARSE_PITCH[size],
                         'hole_count': 2, 'preferred': 1}
    tmpl = [
        {'kind': 'face', 'key': 'plane', 'role': 'plane', 'count': 2,
         'dims': ['size_x', 'size_z'], 'dof_free': ['tx', 'ty', 'rz'],
         'origin_rule': 'the two outer faces that land on the profiles'},
        {'kind': 'bore', 'key': 'M{screw_d}x{P}', 'role': 'socket', 'count': 2,
         'dims': ['screw_d', 'base_thickness'], 'dof_free': ['tz', 'rz'],
         'origin_rule': 'one hole per face at hole_offset from the corner'},
    ]
    b.families.append(_family(
        'bracket-corner', 'Outer L corner bracket', 'frame', 'at-bracket', '',
        ['series', 'hole_count'], '<series>', table, {'kind': 'none'}, tmpl,
        src, 'bracket',
        notes='cast L bracket bolted across the outside corner of two profiles'))
    for series, row in table.items():
        vname = 'bracket-corner-%s' % series
        tk = thread_key('M%s' % _num(row['screw_d']), row['P'])
        dims = dict(row)
        dims.pop('preferred', None)
        feats = [
            _plane(vname, 'face:0', (0, 0, 0), (0, 0, -1),
                   {'size_x': row['size_x'], 'size_z': row['size_z'], 'normal_z': -1}),
            _plane(vname, 'face:1', (0, 0, 0), (-1, 0, 0),
                   {'size_x': row['size_y'], 'size_z': row['size_z'], 'normal_x': -1}),
            _feature(vname, 'hole:0', 'bore', tk, 'socket', (row['hole_offset'], 0, 0),
                     (0, 0, -1), row['base_thickness'],
                     {'d': row['screw_d'], 'depth': row['base_thickness']}, ('tz', 'rz')),
            _feature(vname, 'hole:1', 'bore', tk, 'socket', (0, 0, row['hole_offset']),
                     (-1, 0, 0), row['base_thickness'],
                     {'d': row['screw_d'], 'depth': row['base_thickness']}, ('tz', 'rz')),
        ]
        b.add(_variant(vname, 'bracket-corner', series,
                       'Corner bracket %s-series' % series,
                       {'series': row['series'], 'hole_count': 2},
                       dims, -1, feats), feats)


# ---- ball bearings -----------------------------------------------------------

BB_FIELDS = ['id', 'od', 'w', 'colour', 'or', 'ir', 'fd', 'fw']


def import_bearings(b):
    f = 'ball_bearings.scad'
    tup = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', f))
    table = {}
    for name, vals in tup.items():
        if not name.startswith('BB'):
            continue
        row = dict(zip(BB_FIELDS, vals[1:]))
        row.pop('colour', None)
        row['flanged'] = 1 if row['fd'] else 0
        row['preferred'] = 1
        table[vals[0]] = row
    # 625 plain: the F625 tuple carries the plain bearing's id/od/w; the
    # flange is what F adds. Hand-derived, said so.
    f625 = table['F625']
    table['625'] = {'id': f625['id'], 'od': f625['od'], 'w': f625['w'],
                    'or': f625['or'], 'ir': f625['ir'], 'fd': 0, 'fw': 0,
                    'flanged': 0, 'preferred': 1}
    src = _nop_source(b, f, len(table) - 1, ', '.join(sorted(k for k in table if k != '625')),
                      'fields id od w colour or ir fd fw per the file header '
                      '(or/ir = outer/inner race widths, fd/fw = flange dia/'
                      'width). 625 (plain) is DERIVED here from F625: not a '
                      'NopSCADlib tuple. 6000/6001 are not in the file and were '
                      'not invented; 6200/6201 are the 62xx members present')
    tmpl = [
        {'kind': 'bore', 'key': 'bore-{id}H7', 'role': 'socket', 'count': 1,
         'dims': ['id', 'w'], 'dof_free': ['rz'],
         'origin_rule': 'inner ring, axis +z, centred; takes an h6 shaft'},
        {'kind': 'shaft', 'key': 'bore-{od}H7', 'role': 'male', 'count': 1,
         'dims': ['od', 'w'], 'dof_free': [],
         'origin_rule': 'outer ring into a housing pocket'},
    ]
    b.families.append(_family(
        'bearing-ball', 'Deep-groove radial ball bearing', 'bearing',
        'at-bearing', 'ISO 15', ['bearing_code', 'seal', 'flange'],
        '<bearing_code>', table, {'kind': 'none'}, tmpl, src, 'bearing',
        notes='the key names the FIT (bore-8H7 = an 8 mm H7 bore for an h6 '
              'shaft): the shaft side carries the same key as male. Seal '
              '(open/ZZ/2RS) is not in the tuples: -1'))
    for code, row in table.items():
        vname = 'bearing-ball-%s' % code
        dims = dict(row)
        dims.pop('preferred', None)
        feats = [
            _feature(vname, 'bore', 'bore', 'bore-%sH7' % _num(row['id']), 'socket',
                     (0, 0, 0), (0, 0, 1), row['w'],
                     {'d': row['id'], 'depth': row['w'], 'tolerance': 'H7'}, ('rz',),
                     basis='derived' if code == '625' else 'cited'),
            _feature(vname, 'outer', 'shaft', 'bore-%sH7' % _num(row['od']), 'male',
                     (0, 0, 0), (0, 0, 1), row['w'],
                     {'d': row['od'], 'length': row['w']}, (),
                     basis='derived' if code == '625' else 'cited'),
        ]
        b.add(_variant(vname, 'bearing-ball', code, 'Ball bearing %s' % code,
                       {'bearing_code': code, 'seal': -1, 'flange': row['flanged']},
                       dims, -1, feats,
                       notes='derived from the F625 tuple (plain = flanged minus flange)'
                       if code == '625' else ''), feats)


# ---- linear bushings -------------------------------------------------------

LM_FIELDS = ['L', 'od', 'id', 'gl', 'gd', 'gs']
LM_SEED = ('LM6UU', 'LM8UU', 'LM10UU', 'LM12UU')


def import_bushings(b):
    f = 'linear_bearings.scad'
    tup = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', f))
    table = {}
    for name, vals in tup.items():
        if not name.startswith('LM') or name.endswith('OP'):
            continue
        row = dict(zip(LM_FIELDS, vals[1:7]))
        row['long'] = 1 if 'LUU' in name else 0
        row['preferred'] = 1
        table[name] = row
    src = _nop_source(b, f, len(table), 'LM3UU..LM16UU and LM3LUU..LM16LUU',
                      'fields L od id gl gd gs (groove length/dia/spacing) '
                      'per the file header; LM16UUOP (open) not read')
    tmpl = [
        {'kind': 'bore', 'key': 'bore-{id}H7', 'role': 'socket', 'count': 1,
         'dims': ['id', 'L'], 'dof_free': ['tz', 'rz'],
         'origin_rule': 'ball cage bore, axis +z; slides and turns on an h6 rod'},
        {'kind': 'shaft', 'key': 'bore-{od}H7', 'role': 'male', 'count': 1,
         'dims': ['od', 'L', 'gd', 'gs'], 'dof_free': [],
         'origin_rule': 'outer shell into a housing'},
    ]
    b.families.append(_family(
        'lm-bushing', 'Linear ball bushing LMxUU', 'motion', 'at-linear-bearing',
        '', ['bore', 'cut_length'], '<code>', table, {'kind': 'none'}, tmpl,
        src, 'bushing',
        notes='variants seeded for LM6UU LM8UU LM10UU LM12UU; the long (LUU) '
              'rows stay in the table'))
    for code in LM_SEED:
        row = table[code]
        vname = 'lm-bushing-%s' % code
        dims = dict(row)
        dims.pop('preferred', None)
        feats = [
            _feature(vname, 'bore', 'bore', 'bore-%sH7' % _num(row['id']), 'socket',
                     (0, 0, 0), (0, 0, 1), row['L'],
                     {'d': row['id'], 'depth': row['L'], 'tolerance': 'H7'}, ('tz', 'rz')),
            _feature(vname, 'outer', 'shaft', 'bore-%sH7' % _num(row['od']), 'male',
                     (0, 0, 0), (0, 0, 1), row['L'],
                     {'d': row['od'], 'length': row['L']}, ()),
        ]
        b.add(_variant(vname, 'lm-bushing', code, 'Linear bushing %s' % code,
                       {'bore': row['id'], 'cut_length': row['L']}, dims, -1, feats),
              feats)


# ---- MGN rails + carriages ---------------------------------------------------

RAIL_FIELDS = ['Wr', 'Hr', 'Emin', 'P', 'D', 'd', 'h', 'screw', 'cs_screw', 'go', 'gw']
CARR_FIELDS = ['L', 'L1', 'W', 'H', 'H1', 'C', 'B', 'screw', 'rail']
RAIL_SEED = ('7C', '7H', '9C', '9H', '12C', '12H', '15C')
RAIL_LENGTH_RULE = {'kind': 'continuous', 'min': 100, 'max': 1000, 'step': 50,
                    'notes': 'cut to length (hole pitch P repeats); seeded L300'}


def import_rails(b):
    f = 'rails.scad'
    tup = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', f))
    rails = {n: dict(zip(RAIL_FIELDS, v[1:])) for n, v in tup.items() if n.startswith('MGN') and not n.endswith('_carriage')}
    carrs = {n[:-9]: dict(zip(CARR_FIELDS, v[1:])) for n, v in tup.items() if n.endswith('_carriage') and n.startswith('MGN')}
    table = {}
    for code in RAIL_SEED:
        size, ctype = code[:-1], code[-1]
        r, c = rails['MGN%s' % size], carrs['MGN%s%s' % (size, ctype)]
        row = {'rail_W': r['Wr'], 'rail_H': r['Hr'], 'rail_Emin': r['Emin'],
               'rail_P': r['P'], 'rail_D': r['D'], 'rail_d': r['d'], 'rail_h': r['h'],
               'carriage_L': c['L'], 'carriage_L1': c['L1'], 'carriage_W': c['W'],
               'carriage_H': c['H'], 'carriage_H1': c['H1'], 'carriage_C': c['C'],
               'carriage_B': c['B'],
               'rail_screw_d': float(_screw_ref_key(r['screw'])[1][1:]),
               'carriage_screw_d': float(_screw_ref_key(c['screw'])[1][1:]),
               'preferred': 1}
        table[code] = row
    src = _nop_source(b, f, len(table), 'MGN5..MGN15 rails + MGNxC/H carriages',
                      'rail fields Wr Hr Emin P D d h screw cs_screw go gw; '
                      'carriage fields L L1 W H H1 C B screw rail, per the '
                      'file headers. MGN15 has only a C carriage in the file; '
                      'HGH/SSR not seeded')
    tmpl = [
        {'kind': 'rail', 'key': 'rail-MGN{size}', 'role': 'channel', 'count': 1,
         'dims': ['rail_W', 'rail_H'], 'dof_free': ['tz'],
         'origin_rule': 'the rail body from z=0 to z=L'},
        {'kind': 'rail', 'key': 'rail-MGN{size}', 'role': 'rider', 'count': 1,
         'dims': ['carriage_L', 'carriage_W', 'carriage_H'], 'dof_free': ['tz'],
         'origin_rule': 'the carriage, seeded at mid-rail'},
        {'kind': 'hole_pattern', 'key': 'M{rail_screw}', 'role': 'socket', 'count': 1,
         'dims': ['rail_P', 'rail_D', 'rail_Emin'], 'dof_free': ['tz', 'rz'],
         'origin_rule': 'counterbored rail holes at pitch P from Emin'},
        {'kind': 'hole_pattern', 'key': 'M{carriage_screw}', 'role': 'female', 'count': 1,
         'dims': ['carriage_C', 'carriage_B'], 'dof_free': ['rz'],
         'origin_rule': 'the 4 tapped carriage holes, C x B'},
    ]
    b.families.append(_family(
        'rail-mgn', 'Miniature profile rail MGN + carriage', 'motion',
        'at-linear-rail', '', ['series', 'carriage_length', 'cut_length'],
        '<size><C|H>-L<cut_length>', table, RAIL_LENGTH_RULE, tmpl, src, 'rail',
        notes='one variant = rail size + carriage type (C standard / H long) + '
              'rail length; the pair rides on key rail-MGN<size>'))
    for code, row in table.items():
        size = code[:-1]
        L = 300
        vname = 'rail-mgn-%s-L%d' % (code, L)
        dims = dict(row)
        dims.pop('preferred', None)
        dims['L'] = L
        n_holes = int((L - 2 * row['rail_Emin']) // row['rail_P']) + 1
        rk = thread_key('M%s' % _num(row['rail_screw_d']))
        ck = thread_key('M%s' % _num(row['carriage_screw_d']))
        feats = [
            _feature(vname, 'rail', 'rail', 'rail-MGN%s' % size, 'channel',
                     (0, 0, 0), (0, 0, 1), L,
                     {'W': row['rail_W'], 'H': row['rail_H']}, ('tz',)),
            _feature(vname, 'carriage', 'rail', 'rail-MGN%s' % size, 'rider',
                     (0, 0, L / 2), (0, 0, 1), row['carriage_L'],
                     {'L': row['carriage_L'], 'W': row['carriage_W'],
                      'H': row['carriage_H']}, ('tz',),
                     load={'axial_n': -1, 'shear_n': -1, 'moment_nm': -1,
                           'basis': 'undetermined'}),
            _feature(vname, 'rail-holes', 'hole_pattern', rk, 'socket',
                     (0, 0, row['rail_Emin']), (0, 0, 1), L - 2 * row['rail_Emin'],
                     {'pitch': row['rail_P'], 'count': n_holes, 'D': row['rail_D'],
                      'd': row['rail_d'], 'depth': row['rail_h']}, ('tz', 'rz')),
            _feature(vname, 'carriage-holes', 'hole_pattern', ck, 'female',
                     (0, 0, L / 2), (0, 1, 0), row['carriage_H'] - row['carriage_H1'],
                     {'C': row['carriage_C'], 'B': row['carriage_B'], 'count': 4,
                      'd': row['carriage_screw_d']}, ('rz',)),
        ]
        b.add(_variant(vname, 'rail-mgn', code, 'MGN%s rail %d + MGN%s carriage' % (size, L, code),
                       {'series': 'MGN%s' % size, 'carriage_length': code[-1],
                        'cut_length': L}, dims, L, feats), feats)


# ---- rods (hand-entered) -------------------------------------------------------

ROD_SIZES = (6, 8, 10, 12)
ROD_LENGTH_RULE = {'kind': 'continuous', 'min': 50, 'max': 1000, 'step': 10,
                   'notes': 'cut to length; seeded L300 and L500'}


def import_rods(b):
    src = 'hand:rod'
    b.sources.append(dict(
        name=src, display_name='hand-entered: hardened smooth shaft',
        url='AI-Notes/plans/MECH_KIT_PARTS_CATALOGUE.md#3.1 (ThreadedRod/Pin; '
            'LinearBushing LM{d}UU d in 3..16)', commit='', path='', sha256='',
        bytes=-1, fetched='', rows_imported=len(ROD_SIZES), rows_rejected_json='[]',
        is_prior=True, provenance_id=PROV,
        notes='NopSCADlib has no rod tuple list (vitamins/rod.scad is a '
              'parametric module); the diameters are the LMxUU bushing bores '
              'the catalogue pairs them with. Tolerance h6 is the common '
              'hardened-shaft grade: a KNOB until a datasheet is cited.',
        **HAND_LICENCE))
    table = {str(d): {'d': d, 'tolerance_h6_um': {6: 8, 8: 9, 10: 9, 12: 11}[d],
                      'preferred': 1} for d in ROD_SIZES}
    tmpl = [
        {'kind': 'shaft', 'key': 'bore-{d}H7', 'role': 'male', 'count': 1,
         'dims': ['d'], 'dof_free': ['tz', 'rz'],
         'origin_rule': 'the whole rod from z=0 to z=L'},
        {'kind': 'face', 'key': 'plane', 'role': 'plane', 'count': 2,
         'dims': ['d'], 'dof_free': ['tx', 'ty', 'rz'],
         'origin_rule': 'end faces'},
    ]
    b.families.append(_family(
        'rod', 'Hardened smooth shaft (linear rod)', 'motion', 'at-shaft',
        'ISO 286 h6', ['bore', 'cut_length'], '<d>-L<cut_length>', table,
        ROD_LENGTH_RULE, tmpl, src, 'rod',
        notes='hand-entered sizes 6/8/10/12 (the LM6UU..LM12UU bores); '
              'tolerance_h6_um = ISO 286 h6 band at that diameter (cited '
              'from the ISO 286 table, knob until checked)'))
    for d in ROD_SIZES:
        for L in SEED_PROFILE_LENGTHS:
            vname = 'rod-%d-L%d' % (d, L)
            dims = dict(table[str(d)])
            dims.pop('preferred', None)
            dims['L'] = L
            feats = [
                _feature(vname, 'shaft', 'shaft', 'bore-%dH7' % d, 'male',
                         (0, 0, 0), (0, 0, 1), L, {'d': d, 'length': L},
                         ('tz', 'rz'), basis='knob'),
                _plane(vname, 'end:0', (0, 0, 0), (0, 0, -1), {'d': d, 'normal_z': -1}),
                _plane(vname, 'end:L', (0, 0, L), (0, 0, 1), {'d': d, 'normal_z': 1}),
            ]
            b.add(_variant(vname, 'rod', str(d), 'Shaft %d h6 x %d' % (d, L),
                           {'bore': d, 'cut_length': L}, dims, L, feats,
                           notes='hand-entered (see DimensionSource hand:rod)'), feats)


# ---- TR8 lead screws -------------------------------------------------------------

def import_leadscrews(b):
    f = 'leadnuts.scad'
    tup = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', f))
    src = _nop_source(b, f, 2, 'LSN8x2, LSN8x8',
                      'fields bore shank height flange_dia flange_t flange_offset '
                      'holes hole_dia hole_pitch screw pitch lead flat colour; the '
                      'SCREW dims (d 8, pitch 2, lead 2 / 8) are read from the nut '
                      'tuples (NopSCADlib has no leadscrews.scad). TR8x4 (2-start) is '
                      'hand-entered: ISO 2901 Tr8x4(P2), not in the file')
    table = {}
    for name, lead, hand in (('LSN8x2', 2, False), ('LSN8x8', 8, False)):
        v = tup[name]
        table['TR8x%d' % lead] = {'d': v[2], 'pitch': v[12], 'lead': v[13],
                                  'starts': int(v[13] / v[12]), 'preferred': 1}
    table['TR8x4'] = {'d': 8, 'pitch': 2, 'lead': 4, 'starts': 2, 'preferred': 1}
    tmpl = [
        {'kind': 'thread', 'key': 'Tr8x{lead}', 'role': 'male', 'count': 1,
         'dims': ['d', 'pitch', 'lead', 'starts'], 'dof_free': ['rz'],
         'origin_rule': 'the whole screw from z=0 to z=L; tz coupled to rz by the lead'},
        {'kind': 'face', 'key': 'plane', 'role': 'plane', 'count': 2,
         'dims': ['d'], 'dof_free': ['tx', 'ty', 'rz'], 'origin_rule': 'end faces'},
    ]
    b.families.append(_family(
        'leadscrew-tr8', 'Trapezoidal lead screw TR8 (ISO 2901/2903)', 'transmission',
        'at-leadscrew', 'ISO 2903', ['lead', 'starts', 'cut_length'],
        'TR8x<lead>-L<cut_length>', table, ROD_LENGTH_RULE, tmpl, src, 'leadscrew',
        notes='key Tr8x<lead> is the ISO 2901 designation (Tr8x8(P2) = 4 starts)'))
    for code, row in table.items():
        L = 300
        vname = 'leadscrew-tr8-%s-L%d' % (code, L)
        dims = dict(row)
        dims.pop('preferred', None)
        dims['L'] = L
        feats = [
            _feature(vname, 'thread', 'thread', 'Tr8x%s' % _num(row['lead']), 'male',
                     (0, 0, 0), (0, 0, 1), L,
                     {'d': row['d'], 'pitch': row['pitch'], 'lead': row['lead'],
                      'starts': row['starts'], 'L': L}, ('rz',),
                     basis='knob' if code == 'TR8x4' else 'cited',
                     notes='tz = rz * lead / 2pi'),
            _plane(vname, 'end:0', (0, 0, 0), (0, 0, -1), {'d': row['d'], 'normal_z': -1}),
            _plane(vname, 'end:L', (0, 0, L), (0, 0, 1), {'d': row['d'], 'normal_z': 1}),
        ]
        b.add(_variant(vname, 'leadscrew-tr8', code, '%s(P%s) x %d' % (code.replace('TR', 'Tr'), _num(row['pitch']), L),
                       {'lead': row['lead'], 'starts': row['starts'], 'cut_length': L},
                       dims, L, feats,
                       notes='hand-entered 2-start (not a NopSCADlib tuple)' if code == 'TR8x4' else ''),
              feats)


# ---- GT2 belts + pulleys --------------------------------------------------------

BELT_FIELDS = ['pitch', 'width', 'thickness', 'tooth_height', 'pitch_line_offset']
BELT_LENGTH_RULE = {'kind': 'continuous', 'min': 200, 'max': 5000, 'step': 2,
                    'notes': 'open belt cut to a whole number of teeth (2 mm); '
                             'seeded L1000 and L2000'}
PULLEY_FIELDS = ['type', 'teeth', 'od', 'belt', 'width', 'hub_dia', 'hub_length',
                 'bore', 'flange_dia', 'flange_thickness', 'screw_length',
                 'screw_z', 'screw', 'screws']


def import_belts(b):
    f = 'belts.scad'
    tup = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', f))
    table = {}
    for name in ('GT2x6', 'GT2x9'):
        row = dict(zip(BELT_FIELDS, tup[name][1:]))
        row['preferred'] = 1
        table[str(_num(row['width']))] = row
    src = _nop_source(b, f, len(table), 'GT2x6, GT2x9',
                      'fields pitch width thickness tooth_height pitch_line_offset '
                      'per the file header')
    tmpl = [
        {'kind': 'belt_tooth', 'key': 'GT2-{width}', 'role': 'rider', 'count': 1,
         'dims': ['pitch', 'width', 'thickness'], 'dof_free': ['tz'],
         'origin_rule': 'teeth face -y; belt runs along +z from z=0 to z=L'},
    ]
    b.families.append(_family(
        'belt-gt2', 'GT2 timing belt (2 mm pitch, open)', 'transmission', 'at-belt', '',
        ['tooth_profile', 'belt_width', 'cut_length'], '<width>-L<cut_length>',
        table, BELT_LENGTH_RULE, tmpl, src, 'belt',
        notes='closed loops (by tooth count) are not seeded in mxc-1'))
    for w, row in table.items():
        for L in (1000, 2000):
            vname = 'belt-gt2-%s-L%d' % (w, L)
            dims = dict(row)
            dims.pop('preferred', None)
            dims['L'] = L
            dims['teeth'] = int(L / row['pitch'])
            feats = [_feature(vname, 'teeth', 'belt_tooth', 'GT2-%s' % w, 'rider',
                              (0, 0, 0), (0, 0, 1), L,
                              {'pitch': row['pitch'], 'width': row['width'],
                               'thickness': row['thickness'], 'teeth': dims['teeth']},
                              ('tz',))]
            b.add(_variant(vname, 'belt-gt2', w, 'GT2 belt %s mm x %d' % (w, L),
                           {'tooth_profile': 'GT2', 'belt_width': int(w), 'cut_length': L},
                           dims, L, feats), feats)


def import_pulleys(b):
    f = 'pulleys.scad'
    tup = parse_scad_tuples(os.path.join(UPSTREAM, NOP_DIR, 'vitamins', f))
    picks = (('16T-b5', 'GT2x16_pulley'), ('20T-b5', 'GT2x20ob_pulley'),
             ('16T-b5-w9', 'GT2x16_pulley_9'), ('20T-b5-w9', 'GT2x20_pulley_9'))
    table = {}
    for code, name in picks:
        v = tup[name]
        row = dict(zip(PULLEY_FIELDS, v[1:]))
        row['belt_width'] = {'GT2x6': 6, 'GT2x9': 9}[row.pop('belt')]
        row['grub_d'] = float(_screw_ref_key(row.pop('screw'))[1][1:])
        row.pop('type', None)
        row['preferred'] = 1
        row['basis_knob'] = 0
        table[code] = row
    for code in ('16T-b5', '20T-b5'):
        row = dict(table[code])
        row['bore'] = 8
        row['basis_knob'] = 1
        table[code.replace('b5', 'b8')] = row
    src = _nop_source(b, f, 4, 'GT2x16_pulley, GT2x20ob_pulley, GT2x16_pulley_9, GT2x20_pulley_9',
                      'fields name type teeth od belt width hub_dia hub_length bore '
                      'flange_dia flange_thickness screw_length screw_z screw screws '
                      'per the file header. The bore-8 variants are HAND-ENTERED '
                      '(the bore-5 tuple with bore=8; basis knob, not in the file)')
    tmpl = [
        {'kind': 'bore', 'key': 'bore-{bore}H7', 'role': 'socket', 'count': 1,
         'dims': ['bore', 'hub_length'], 'dof_free': [],
         'origin_rule': 'hub bore, axis +z, clamped by the grub screws'},
        {'kind': 'belt_tooth', 'key': 'GT2-{belt_width}', 'role': 'channel', 'count': 1,
         'dims': ['teeth', 'od', 'width'], 'dof_free': ['rz'],
         'origin_rule': 'the toothed rim'},
        {'kind': 'thread', 'key': 'M{grub}x{P}', 'role': 'female', 'count_rule': 'screws',
         'dims': ['grub_d', 'screw_z'], 'dof_free': ['rz'],
         'origin_rule': 'grub screw holes in the hub, radial'},
    ]
    b.families.append(_family(
        'pulley-gt2', 'GT2 timing pulley', 'transmission', 'at-pulley', '',
        ['tooth_profile', 'teeth', 'bore', 'belt_width'], '<teeth>T-b<bore>[-w<belt_width>]',
        table, {'kind': 'none'}, tmpl, src, 'pulley',
        notes='16T/20T, bore 5 from the tuples; bore 8 hand-entered (basis_knob=1)'))
    for code, row in table.items():
        vname = 'pulley-gt2-%s' % code
        dims = dict(row)
        dims.pop('preferred', None)
        knob = dims.pop('basis_knob')
        basis = 'knob' if knob else 'cited'
        gk = thread_key('M%s' % _num(row['grub_d']))
        feats = [
            _feature(vname, 'bore', 'bore', 'bore-%sH7' % _num(row['bore']), 'socket',
                     (0, 0, 0), (0, 0, 1), row['hub_length'] + row['width'],
                     {'d': row['bore'], 'depth': row['hub_length'] + row['width']}, (),
                     basis=basis),
            _feature(vname, 'teeth', 'belt_tooth', 'GT2-%s' % _num(row['belt_width']), 'channel',
                     (0, 0, row['hub_length']), (0, 0, 1), row['width'],
                     {'teeth': row['teeth'], 'od': row['od'], 'width': row['width']},
                     ('rz',), basis=basis),
        ]
        for i in range(int(row['screws'])):
            feats.append(_feature(vname, 'grub:%d' % i, 'thread', gk, 'female',
                                  (0, 0, row['screw_z']), (1, 0, 0) if i == 0 else (0, 1, 0),
                                  row['hub_dia'] / 2 - row['bore'] / 2,
                                  {'pitch': COARSE_PITCH['M%s' % _num(row['grub_d'])],
                                   'd': row['grub_d']}, ('rz',), basis=basis))
        b.add(_variant(vname, 'pulley-gt2', code, 'GT2 pulley %s' % code,
                       {'tooth_profile': 'GT2', 'teeth': row['teeth'], 'bore': row['bore'],
                        'belt_width': row['belt_width']}, dims, -1, feats,
                       notes='hand-entered bore-8: tuple dims of the bore-5 part with the bore set to 8; verify before buying'
                       if knob else ''), feats)


# --------------------------------------------------------------------
# 3. Gridfinity (constants from gridfinity-rebuilt standard.scad)
# --------------------------------------------------------------------

GF_SPEC = 'https://gridfinity.xyz/specification/'


def gridfinity_constants():
    c = parse_scad_constants(os.path.join(UPSTREAM, GF_DIR, 'src', 'core', 'standard.scad'))
    bp = c['BASE_PROFILE']
    lip = c['STACKING_LIP_LINE']
    return {
        'grid': c['GRID_DIMENSIONS_MM'][0],
        'height_unit': c['BASE_HEIGHT'],
        'base_top': c['BASE_TOP_DIMENSIONS'][0],
        'base_gap': _num(c['GRID_DIMENSIONS_MM'][0] - c['BASE_TOP_DIMENSIONS'][0]),
        'base_profile_h': _num(bp[3][1]),
        'base_profile_x': _num(bp[3][0]),
        'base_profile_steps': _j([bp[1][0], bp[2][1] - bp[1][1], bp[3][0] - bp[2][0]]),
        'base_top_radius': c['BASE_TOP_RADIUS'],
        'lip_h': _num(lip[3][1]),
        'lip_x': _num(lip[3][0]),
        'lip_steps': _j([lip[1][0], lip[2][1] - lip[1][1], lip[3][0] - lip[2][0]]),
        'lip_fillet_r': c['STACKING_LIP_FILLET_RADIUS'],
        'lip_support_h': c['STACKING_LIP_SUPPORT_HEIGHT'],
        'magnet_d': _num(c['MAGNET_HOLE_RADIUS'] * 2),
        'magnet_h': c['MAGNET_HEIGHT'],
        'magnet_hole_depth': _num(c['MAGNET_HOLE_DEPTH']),
        'screw_d': _num(c['SCREW_HOLE_RADIUS'] * 2),
        'hole_from_side': c['d_hole_from_side'],
        'hole_from_bottom_edge': c['HOLE_DISTANCE_FROM_BOTTOM_EDGE'],
        'wall': c['d_wall'],
        'divider': c['d_div'],
        'inner_fillet_r': c['r_f2'],
        'baseplate_counterbore_d': _num(c['BASEPLATE_SCREW_COUNTERBORE_RADIUS'] * 2),
        'baseplate_counterbore_h': c['BASEPLATE_SCREW_COUNTERBORE_HEIGHT'],
        'layer_height': c['LAYER_HEIGHT'],
    }


def _gf_source(b, rows, what):
    src = 'gridfinity-rebuilt:standard.scad'
    if not any(s['name'] == src for s in b.sources):
        b.sources.append(_source_row(
            src, GF_DIR, 'src/core/standard.scad', GF_COMMIT, GF_LICENCE, GF_URL,
            rows, [],
            notes='constants read: GRID_DIMENSIONS_MM, BASE_HEIGHT (= the 7 mm '
                  'height unit), BASE_TOP_DIMENSIONS, BASE_PROFILE, '
                  'STACKING_LIP_LINE, MAGNET_HOLE_RADIUS/MAGNET_HEIGHT/'
                  'MAGNET_HOLE_DEPTH, SCREW_HOLE_RADIUS, d_hole_from_side, '
                  'HOLE_DISTANCE_FROM_BOTTOM_EDGE, d_wall, d_div, r_f2, '
                  'BASEPLATE_SCREW_COUNTERBORE_*, LAYER_HEIGHT. Spec cited: '
                  + GF_SPEC))
    return src


def _cell_features(vname, nx, ny, z, axis, tag, gf, with_holes, basis='derived',
                   kind='grid_cell'):
    """nx*ny grid cells at z with the four magnet + screw sockets each
    (holes at hole_from_side from the cell edge, i.e. +-(grid/2 - 8))."""
    g = gf['grid']
    off = g / 2 - gf['hole_from_side']
    feats = []
    for j in range(ny):
        for i in range(nx):
            cx, cy = i * g, j * g
            feats.append(_feature(vname, '%s:%d,%d' % (tag, i, j), kind,
                                  'grid-%s' % _num(g), 'cell', (cx, cy, z), axis, gf['base_profile_h'],
                                  {'grid': g, 'base_top': gf['base_top'],
                                   'profile_h': gf['base_profile_h']}, (), basis=basis))
            if not with_holes:
                continue
            for cname, sx, sy in (('ne', 1, 1), ('nw', -1, 1), ('sw', -1, -1), ('se', 1, -1)):
                feats.append(_feature(vname, 'magnet:%d,%d:%s' % (i, j, cname), 'magnet',
                                      'magnet-%sx%s' % (_num(gf['magnet_d']), _num(gf['magnet_h'])),
                                      'socket', (cx + sx * off, cy + sy * off, z), axis,
                                      gf['magnet_hole_depth'],
                                      {'d': gf['magnet_d'], 'depth': gf['magnet_hole_depth']}, (),
                                      basis=basis))
                feats.append(_feature(vname, 'screw:%d,%d:%s' % (i, j, cname), 'counterbore',
                                      'counterbore-M3', 'socket',
                                      (cx + sx * off, cy + sy * off, z), axis, gf['height_unit'],
                                      {'d': gf['screw_d'], 'depth': gf['height_unit']}, (),
                                      basis=basis))
    return feats


GF_BIN_SEED = ((1, 1, 3), (1, 1, 6), (2, 2, 6), (2, 3, 6), (3, 2, 6))
GF_PLATE_SEED = ((1, 1), (2, 2), (2, 3))


def import_gridfinity(b):
    gf = gridfinity_constants()
    src = _gf_source(b, len(gf), 'constants')
    table = {'unit': dict(gf)}
    axes = ['grid_x', 'grid_y', 'height_u']
    bin_tmpl = [
        {'kind': 'grid_cell', 'key': 'grid-{grid}', 'role': 'cell', 'count_rule': 'grid_x*grid_y',
         'dims': ['base_top', 'base_profile_h'], 'dof_free': [],
         'origin_rule': 'bottom: one base per cell, (i*42, j*42, 0), normal -z'},
        {'kind': 'magnet', 'key': 'magnet-{magnet_d}x{magnet_h}', 'role': 'socket',
         'count_rule': '4*grid_x*grid_y', 'dims': ['magnet_d', 'magnet_hole_depth'],
         'dof_free': [], 'origin_rule': 'four per base at +-(21-8) from the cell centre'},
        {'kind': 'counterbore', 'key': 'counterbore-M3', 'role': 'socket',
         'count_rule': '4*grid_x*grid_y', 'dims': ['screw_d'], 'dof_free': [],
         'origin_rule': 'under each magnet socket'},
        {'kind': 'lip', 'key': 'grid-{grid}', 'role': 'cell', 'count_rule': 'grid_x*grid_y',
         'dims': ['lip_h', 'lip_x'], 'dof_free': [],
         'origin_rule': 'top: the stacking lip accepts another bin\'s bases, normal +z'},
    ]
    b.families.append(_family(
        'gridfinity-bin', 'Gridfinity bin', 'storage', 'at-gridfinity-bin',
        'Gridfinity 1.0', axes, '<grid_x>x<grid_y>x<height_u>', table,
        {'kind': 'stepped', 'series': [2, 3, 4, 5, 6, 7, 8, 9, 10, 12],
         'per_size': {'height_u': [2, 20]}, 'notes': 'height = height_u * 7 mm'},
        bin_tmpl, src, 'printed',
        notes='footprint = grid*n - gap (0.5); height = height_u * height_unit '
              '(7); bottom bases are grid cells (cell<->cell with a baseplate '
              'or the lip of the bin below)', standard_url=GF_SPEC))
    for nx, ny, nz in GF_BIN_SEED:
        code = '%dx%dx%d' % (nx, ny, nz)
        vname = 'gridfinity-bin-%s' % code
        g = gf['grid']
        h = nz * gf['height_unit']
        dims = {'footprint_x': _num(nx * g - gf['base_gap']),
                'footprint_y': _num(ny * g - gf['base_gap']),
                'height': _num(h), 'cells': nx * ny, 'height_u': nz,
                'wall': gf['wall'], 'lip_h': gf['lip_h'],
                'base_profile_h': gf['base_profile_h']}
        feats = _cell_features(vname, nx, ny, 0, (0, 0, -1), 'cell', gf, True)
        feats += _cell_features(vname, nx, ny, h, (0, 0, 1), 'lip', gf, False, kind='lip')
        b.add(_variant(vname, 'gridfinity-bin', code, 'Gridfinity bin %s' % code,
                       {'grid_x': nx, 'grid_y': ny, 'height_u': nz}, dims, h, feats), feats)

    plate_tmpl = [
        {'kind': 'grid_cell', 'key': 'grid-{grid}', 'role': 'cell', 'count_rule': 'grid_x*grid_y',
         'dims': ['base_profile_h'], 'dof_free': [],
         'origin_rule': 'top: one pocket per cell, normal +z'},
        {'kind': 'magnet', 'key': 'magnet-{magnet_d}x{magnet_h}', 'role': 'socket',
         'count_rule': '4*grid_x*grid_y', 'dims': ['magnet_d'], 'dof_free': [],
         'origin_rule': 'four per pocket, matching the bin\'s'},
        {'kind': 'counterbore', 'key': 'counterbore-M3', 'role': 'socket',
         'count_rule': '4*grid_x*grid_y', 'dims': ['baseplate_counterbore_d'],
         'dof_free': [], 'origin_rule': 'under each magnet socket'},
        {'kind': 'face', 'key': 'plane', 'role': 'plane', 'count': 1,
         'dims': [], 'dof_free': ['tx', 'ty', 'rz'], 'origin_rule': 'bottom face'},
    ]
    b.families.append(_family(
        'gridfinity-baseplate', 'Gridfinity baseplate', 'storage', 'at-gridfinity-bin',
        'Gridfinity 1.0', ['grid_x', 'grid_y'], '<grid_x>x<grid_y>', table,
        {'kind': 'none'}, plate_tmpl, src, 'printed',
        notes='footprint = grid*n exactly (no gap: the plate is the grid); '
              'thickness = base_profile_h (4.75) for the thin plate, more '
              'when weighted/skeletonised (not seeded)', standard_url=GF_SPEC))
    for nx, ny in GF_PLATE_SEED:
        code = '%dx%d' % (nx, ny)
        vname = 'gridfinity-baseplate-%s' % code
        g = gf['grid']
        t = gf['base_profile_h']
        dims = {'footprint_x': _num(nx * g), 'footprint_y': _num(ny * g),
                'thickness': t, 'cells': nx * ny}
        feats = _cell_features(vname, nx, ny, t, (0, 0, 1), 'cell', gf, True)
        feats.append(_plane(vname, 'bottom', (0, 0, 0), (0, 0, -1), {'normal_z': -1}))
        b.add(_variant(vname, 'gridfinity-baseplate', code, 'Gridfinity baseplate %s' % code,
                       {'grid_x': nx, 'grid_y': ny}, dims, -1, feats), feats)

    lid_tmpl = [
        {'kind': 'grid_cell', 'key': 'grid-{grid}', 'role': 'cell', 'count_rule': 'grid_x*grid_y',
         'dims': ['base_profile_h'], 'dof_free': [],
         'origin_rule': 'top: bases so bins stack on the lid, normal +z'},
        {'kind': 'lip', 'key': 'grid-{grid}', 'role': 'cell', 'count_rule': 'grid_x*grid_y',
         'dims': ['lip_h'], 'dof_free': [],
         'origin_rule': 'bottom: the skirt that sits into the bin\'s stacking lip, normal -z'},
    ]
    b.families.append(_family(
        'gridfinity-lid', 'Gridfinity lid (stackable)', 'storage', 'at-gridfinity-bin',
        'Gridfinity 1.0', ['grid_x', 'grid_y'], '<grid_x>x<grid_y>', table,
        {'kind': 'none'}, lid_tmpl, src, 'printed',
        notes='HAND-DERIVED from the same constants (no lid in '
              'gridfinity-rebuilt standard.scad): a plate one height unit (7) '
              'thick whose underside is a base profile that drops into the '
              'bin lip and whose top carries bases. Basis derived/knob.',
        standard_url=GF_SPEC))
    for nx, ny in GF_PLATE_SEED:
        code = '%dx%d' % (nx, ny)
        vname = 'gridfinity-lid-%s' % code
        g = gf['grid']
        t = gf['height_unit']
        dims = {'footprint_x': _num(nx * g - gf['base_gap']),
                'footprint_y': _num(ny * g - gf['base_gap']),
                'thickness': t, 'cells': nx * ny}
        feats = _cell_features(vname, nx, ny, t, (0, 0, 1), 'cell', gf, False, basis='knob')
        feats += _cell_features(vname, nx, ny, 0, (0, 0, -1), 'lip', gf, False, basis='knob',
                                kind='lip')
        b.add(_variant(vname, 'gridfinity-lid', code, 'Gridfinity lid %s' % code,
                       {'grid_x': nx, 'grid_y': ny}, dims, -1, feats,
                       notes='hand-derived (see family notes)'), feats)


# --------------------------------------------------------------------
# 4. Drawer slide (hand-entered, plan mxc-1 row; rated load = knob)
# --------------------------------------------------------------------

SLIDE_LENGTHS = list(range(250, 601, 50))
SLIDE = {'height': 45, 'thickness_per_side': 12.7, 'members': 3,
         'extension_ratio': 1.0, 'rated_load_kg_pair': 45,
         'mount_screw_d': 4, 'mount_hole_count_per_member': 4,
         'ball_retainer': 1, 'preferred': 1}


def import_drawer_slides(b):
    src = 'hand:drawer-slide'
    b.sources.append(dict(
        name=src, display_name='hand-entered: 45 mm ball-bearing side-mount drawer slide',
        url='AI-Notes/plans/MECH_FREECAD_INTERCHANGE_PLAN.md#4 (row mxc-1), D-mxc-5',
        commit='', path='', sha256='', bytes=-1, fetched='',
        rows_imported=len(SLIDE_LENGTHS), rows_rejected_json='[]',
        is_prior=True, provenance_id=PROV,
        notes='The plan\'s own numbers: 45 mm high, 12.7 mm per side, lengths '
              '250-600 step 50, 3-fold full extension. The rated load (45 kg '
              'per pair, the common "100 lb" class) is a KNOB with basis knob '
              'until a datasheet is cited; the mounting screw (M4 / #8) and '
              'hole count are knobs too.',
        **HAND_LICENCE))
    table = {str(L): dict(SLIDE, length=L, travel=L) for L in SLIDE_LENGTHS}
    tmpl = [
        {'kind': 'rail', 'key': 'slide-45-ball', 'role': 'channel', 'count': 1,
         'dims': ['height', 'thickness_per_side', 'length'], 'dof_free': ['tz'],
         'origin_rule': 'cabinet member from z=0 to z=L'},
        {'kind': 'rail', 'key': 'slide-45-ball', 'role': 'rider', 'count': 1,
         'dims': ['height', 'travel'], 'dof_free': ['tz'],
         'origin_rule': 'drawer member; travel = L (full extension)'},
        {'kind': 'hole_pattern', 'key': 'M4x0.7', 'role': 'socket', 'count': 2,
         'dims': ['mount_screw_d', 'mount_hole_count_per_member'], 'dof_free': ['tz', 'rz'],
         'origin_rule': 'mounting slots on the cabinet and drawer members'},
        {'kind': 'face', 'key': 'plane', 'role': 'plane', 'count': 2,
         'dims': ['height', 'length'], 'dof_free': ['tx', 'ty', 'rz'],
         'origin_rule': 'the cabinet-side face (-x) and the drawer-side face (+x)'},
    ]
    b.families.append(_family(
        'drawer-slide', 'Ball-bearing side-mount drawer slide, 45 mm, full extension',
        'hardware', 'at-drawer-slide', '', ['cut_length'], 'L<length>', table,
        {'kind': 'stepped', 'series': SLIDE_LENGTHS, 'per_size': {'L': [250, 600]}},
        tmpl, src, 'slide',
        notes='steel members, zinc plated (D-mxc-5); rated_load_kg_pair is a knob'))
    for L in SLIDE_LENGTHS:
        vname = 'drawer-slide-L%d' % L
        dims = dict(table[str(L)])
        dims.pop('preferred', None)
        load = {'axial_n': -1, 'shear_n': _num(round(SLIDE['rated_load_kg_pair'] * 9.81 / 2, 1)),
                'moment_nm': -1, 'basis': 'knob',
                'notes': 'per slide = half the pair rating; a knob'}
        t = SLIDE['thickness_per_side']
        feats = [
            _feature(vname, 'cabinet', 'rail', 'slide-45-ball', 'channel', (0, 0, 0), (0, 0, 1), L,
                     {'height': SLIDE['height'], 'thickness': t, 'length': L}, ('tz',),
                     load=load, basis='knob'),
            _feature(vname, 'drawer', 'rail', 'slide-45-ball', 'rider', (t, 0, 0), (0, 0, 1), L,
                     {'height': SLIDE['height'], 'travel': L}, ('tz',), load=load, basis='knob'),
            _feature(vname, 'holes:cabinet', 'hole_pattern', 'M4x0.7', 'socket', (0, 0, 0), (-1, 0, 0), t,
                     {'d': SLIDE['mount_screw_d'], 'count': SLIDE['mount_hole_count_per_member']},
                     ('tz', 'rz'), basis='knob'),
            _feature(vname, 'holes:drawer', 'hole_pattern', 'M4x0.7', 'socket', (t, 0, 0), (1, 0, 0), t,
                     {'d': SLIDE['mount_screw_d'], 'count': SLIDE['mount_hole_count_per_member']},
                     ('tz', 'rz'), basis='knob'),
            _plane(vname, 'face:cabinet', (0, 0, 0), (-1, 0, 0), {'height': SLIDE['height'], 'length': L, 'normal_x': -1}),
            _plane(vname, 'face:drawer', (t, 0, 0), (1, 0, 0), {'height': SLIDE['height'], 'length': L, 'normal_x': 1}),
        ]
        b.add(_variant(vname, 'drawer-slide', str(L), 'Drawer slide 45 mm x %d full extension' % L,
                       {'cut_length': L}, dims, L, feats,
                       notes='hand-entered (see DimensionSource hand:drawer-slide)'), feats)


# --------------------------------------------------------------------
# driver
# --------------------------------------------------------------------

def build():
    b = Bundle()
    import_screws(b)
    import_nuts(b)
    import_washers(b)
    import_din508(b)
    import_extrusions(b)
    import_tnuts(b)
    import_brackets(b)
    import_bearings(b)
    import_bushings(b)
    import_rails(b)
    import_rods(b)
    import_leadscrews(b)
    import_belts(b)
    import_pulleys(b)
    import_gridfinity(b)
    import_drawer_slides(b)
    _check_unique(b)
    return b


def _check_unique(b):
    for label, rows in (('sources', b.sources), ('families', b.families),
                        ('variants', b.variants), ('features', b.features)):
        names = [r['name'] for r in rows]
        dup = sorted({n for n in names if names.count(n) > 1})
        if dup:
            raise SystemExit('duplicate %s: %s' % (label, dup))


def _literal(rows):
    """Rows as Python literals, one row per line: repr of a dict with
    plain str/int/float/bool values is valid Python and round-trips."""
    return '[\n' + ''.join('    %r,\n' % r for r in rows) + ']\n'


def write_seed(b, path):
    shas = {}
    for d in (FS_DIR, NOP_DIR, GF_DIR):
        sj = json.load(open(os.path.join(UPSTREAM, d, 'SOURCE.json')))
        shas[d] = (sj['commit'], len(sj['files']), sum(f['bytes'] for f in sj['files']))
    head = '''"""
@module mech.mech_catalog_seed

mxc-1 seeds: the STANDARD-PARTS CATALOGUE as rows — GENERATED, do not
hand-edit. Regenerate from modules/mech/ with

    python3 -I custom/catalog_import.py --write

which parses the verbatim upstream tables under custom/upstream/ (each
directory has a SOURCE.json with every file's sha256 and the licence)
and rewrites this file as Python literals. Data only: four lists of
dicts, nothing executed.

Upstream pinned at generation (commit / files / bytes):
%s
Counts: %d DimensionSource, %d MechPartFamily, %d MechPartVariant,
%d MechFeature.

Scope: variants M2-M8 for every threaded family, every nominal length
of the standard's series inside the WB *range table; extrusions 1515..
4080 at L300 and L500 (the length rule says 100-1000); Gridfinity bins
1x1x3 1x1x6 2x2x6 2x3x6 3x2x6, baseplates and lids 1x1 2x2 2x3; drawer
slides L250..L600 step 50. Hand-entered rows (rod, TR8x4, bore-8 GT2
pulleys, Gridfinity lid, bearing 625) carry a note and a knob/derived
basis.

@consumers polariServer (seed_pairs), mech.mech_catalog_selftest,
mech.custom.compatibility
"""

PROV = %r

''' % (''.join('  %s: %s (%d files, %d bytes)\n' % (d, c, n, nb) for d, (c, n, nb) in shas.items()),
       len(b.sources), len(b.families), len(b.variants), len(b.features), PROV)
    body = (head
            + 'SEED_DIMENSION_SOURCES = ' + _literal(b.sources) + '\n'
            + 'SEED_PART_FAMILIES = ' + _literal(b.families) + '\n'
            + 'SEED_PART_VARIANTS = ' + _literal(b.variants) + '\n'
            + 'SEED_FEATURES = ' + _literal(b.features))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(body)
    ast.parse(body)  # it must be a valid Python literal module


def main(argv):
    b = build()
    print('sources %d, families %d, variants %d, features %d' % (
        len(b.sources), len(b.families), len(b.variants), len(b.features)))
    for fam in b.families:
        nv = sum(1 for v in b.variants if v['family_ref'] == fam['name'])
        nf = sum(1 for f in b.features if f['variant_ref'].startswith(fam['name'] + '-'))
        print('  %-22s %4d variants %5d features  <- %s' % (fam['name'], nv, nf, fam['dimension_source_ref']))
    if '--write' in argv:
        out = os.path.join(MECH_DIR, 'mech_catalog_seed.py')
        write_seed(b, out)
        print('wrote', out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

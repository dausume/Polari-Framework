"""
@module mech.custom.material_registry

The registry → rows bridge (mxc-1, plan 3.3 / 9.1 / D-mxc-9):

- `options_from_registry()` / `preferences_from_registry()` build the
  seed dicts for MechMaterialOption / MechMaterialPreference from
  custom/registry/*.json + custom/registry/material_properties.py
  (build_seed.py freezes them into mech_material_seed.py).
- `preference_check(manager, preference_name)` runs COMPOSITION's
  `role_viability()` for every default / alternative id of a
  preference against its MechMaterialOption properties — the
  preference owns no predicates (section 9.1's rule).
- `legacy_comparison(manager, preference_name)` lists the legacy ids
  with their IARC reasons next to the defaults, for the export
  report / the view.

Reads rows through manager.objectTables (fake managers in selftests,
the live manager on a server); refuses by name when a table or row is
missing, never silently empty.

@consumers mech.mech_material_seed (via build_seed), mech.mech_material_selftest,
mech API (mxc-2+), the export report (mxc-5)
"""

import json
import os
import re

from composition.custom import data_refs
from composition.custom.data_refs import material_prop, rows
from composition.custom.part_roles import ROLE_REQUIREMENTS, role_viability
from mech.objects.material._shared import CLASS_ALIASES, worst_iarc

REGISTRY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'registry')
PROV = 'mxc-1'

#: preference name (slug of the registry's part string) -> the
#: composition roles the part plays. Keys of ROLE_REQUIREMENTS ONLY
#: (asserted at import). A slide = sliding + static-structural, a
#: screw = static-structural, a seal = sliding; the bearing and the
#: belt are 'moving' and so ask for a fatigue_class — the polymer rows
#: do not state one, and that reads UNASSESSED, which is the point.
PREFERENCE_ROLE_REFS = {
    't_slot_v_slot_extrusion': ['static-structural'],
    'cast_corner_cube_bracket': ['static-structural'],
    'flat_joining_plate': ['static-structural'],
    'end_cap': ['press-fitted'],
    't_nut_sliding_drop_in_roll_in': ['static-structural'],
    'socket_cap_button_countersunk_set': ['static-structural'],
    'hex_flange_thin': ['static-structural'],
    'nyloc': ['static-structural'],
    'flat_large_spring': ['static-structural'],
    'heat_set_insert': ['press-fitted', 'static-structural'],
    'hex_standoff_pillar': ['static-structural'],
    'threaded_rod': ['static-structural'],
    'dowel_spring_pin': ['press-fitted'],
    'circlip_e_clip': ['static-structural'],
    'deep_groove_ball_bearing': ['moving', 'colliding'],
    'linear_bushing_lmxuu': ['sliding', 'static-structural'],
    'profile_rail_carriage': ['sliding', 'static-structural'],
    'smooth_shaft': ['sliding', 'static-structural'],
    'v_slot_wheel': ['sliding', 'static-structural'],
    'low_friction_slider_pad': ['sliding', 'static-structural'],
    'timing_belt_body': ['moving'],
    'timing_belt_cords': ['moving'],
    'timing_pulley_idler': ['colliding', 'static-structural'],
    'lead_screw': ['sliding', 'static-structural'],
    'lead_screw_nut': ['sliding', 'static-structural'],
    'shaft_coupling': ['static-structural'],
    'coupling_spider_jaw': ['press-fitted'],
    'spur_gear': ['colliding', 'moving'],
    'spring': ['moving'],
    'magnet': ['torque-magnet-active'],
    'cable_chain_zip_tie': ['moving'],
    'cable_insulation_tubing': [],
    'levelling_foot_pad_damper': ['static-structural'],
    'gasket_seal': ['sliding'],
    'printed_bracket_mount': ['static-structural'],
}
_bad = {r for rs in PREFERENCE_ROLE_REFS.values() for r in rs
        if r not in ROLE_REQUIREMENTS}
assert not _bad, f'PREFERENCE_ROLE_REFS names non-composition roles: {_bad}'

#: registry id -> MaterialsScienceMaterial.name where one exists.
MSCI_REFS = {'stainless_a2_a4': 'stainless-steel'}


def slug(text):
    return re.sub(r'_+', '_',
                  re.sub(r'[^a-z0-9]+', '_', text.lower())).strip('_')


def load_registry(registry_dir=REGISTRY_DIR):
    with open(os.path.join(registry_dir, 'materials_registry.json')) as f:
        materials = json.load(f)
    with open(os.path.join(registry_dir, 'part_material_roles.json')) as f:
        roles = json.load(f)
    return materials, roles


def _props_json(table):
    """material_properties.PROPERTIES[id] -> properties_json text in
    the MagneticMaterialOption entry shape."""
    out = {}
    for prop, spec in (table or {}).items():
        value, unit, provenance = spec[0], spec[1], spec[2]
        entry = {'value': value, 'unit': unit, 'provenance': provenance}
        if len(spec) > 3:
            entry['note'] = spec[3]
        out[prop] = entry
    return json.dumps(out, sort_keys=True)


def options_from_registry(registry_dir=REGISTRY_DIR, properties=None):
    """Seed dicts for MechMaterialOption, one per registry material,
    in registry order."""
    if properties is None:
        from mech.custom.registry.material_properties import PROPERTIES
        properties = PROPERTIES
    materials, _ = load_registry(registry_dir)
    out = []
    for m in materials['materials']:
        feed = m.get('feedstocks', [])
        out.append({
            'name': m['id'],
            'display_name': m['name'],
            'material_class': CLASS_ALIASES.get(m['cls'], m['cls']),
            'realization_level': 'literature-demonstrated',
            'item_ref': '',
            'msci_material_ref': MSCI_REFS.get(m['id'], ''),
            'forms_json': '[]',
            'properties_json': _props_json(properties.get(m['id'])),
            'role_overrides_json': '{}',
            'is_reference_only': m['status'] == 'legacy_harmful',
            'is_prior': True,
            'status': m['status'],
            'feedstocks_json': json.dumps(feed),
            'worst_feedstock_iarc': worst_iarc(feed),
            'end_of_life': m.get('end_of_life', ''),
            'bio_option': bool(m.get('bio_option', False)),
            'caveats_json': json.dumps(m.get('caveats', [])),
            'replaced_by_json': json.dumps(m.get('replaced_by', [])),
            'confidence': m.get('confidence', 'check'),
            'source': m.get('source', 'collab-mech-parts'),
            'provenance_id': PROV,
            'notes': m.get('note', ''),
        })
    return out


def _dedupe(ids):
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def preferences_from_registry(registry_dir=REGISTRY_DIR):
    """Seed dicts for MechMaterialPreference, one per registry part
    role, in registry order; name = slug(part)."""
    _, roles = load_registry(registry_dir)
    out = []
    for r in roles['part_material_roles']:
        name = slug(r['part'])
        out.append({
            'name': name,
            'category': r['category'],
            'part': r['part'],
            'display_name': r['part'],
            'default_ids_json': json.dumps(_dedupe(r['default_ids'])),
            'alternative_ids_json': json.dumps(_dedupe(r['alternative_ids'])),
            'legacy_ids_json': json.dumps(_dedupe(r['legacy_ids'])),
            'polari_default_json': json.dumps(r['polari_default']),
            'polari_alternatives_json': json.dumps(r['polari_alternatives']),
            'legacy_harmful_json': json.dumps(r['legacy_harmful']),
            'role_refs_json': json.dumps(PREFERENCE_ROLE_REFS.get(name, [])),
            'notes': r.get('notes', ''),
            'is_prior': True,
            'provenance_id': PROV,
        })
    return out


# ---------------------------------------------------------------- lookups

def _named(manager, class_name, name):
    for row in rows(manager, class_name):
        if getattr(row, 'name', None) == name:
            return row
    return None


def _loads(text, default):
    try:
        v = json.loads(text or '')
    except (TypeError, ValueError):
        return default
    return v if isinstance(v, type(default)) else default


def preference(manager, preference_name):
    """(row, refusal) — exactly one is non-None."""
    tables = getattr(manager, 'objectTables', {}) or {}
    if 'MechMaterialPreference' not in tables:
        return None, {'refusal': 'MechMaterialPreference table is not '
                                 'booted', 'kind': 'module-not-booted'}
    row = _named(manager, 'MechMaterialPreference', preference_name)
    if row is None:
        near = [p for p in (getattr(r, 'name', '')
                            for r in rows(manager, 'MechMaterialPreference'))
                if slug(preference_name) in p
                or any(tok in p for tok in slug(preference_name).split('_')
                       if len(tok) > 3)]
        return None, {'refusal': f'no MechMaterialPreference named '
                                 f'"{preference_name}"',
                      'kind': 'no-such-row', 'nearest': near[:5]}
    return row, None


def option(manager, material_id):
    return _named(manager, 'MechMaterialOption', material_id)


def preference_check(manager, preference_name):
    """Run composition's role_viability() for every default and
    alternative id of the preference against that id's
    MechMaterialOption properties (read through material_prop, i.e.
    through MATERIAL_PROPERTY_CLASSES — if mech is not registered
    there, every id comes back unassessed and `registered` says why).

    Returns {ok, preference, roles, registered, ids: {id: {tier,
    verdict, viable, missing_props, failed_predicates, degraded}}}.
    missing_props = the properties the roles asked for that the row
    does not state (UNASSESSED, never a pass); failed_predicates = the
    role/property pairs whose stated value fails the threshold."""
    pref, refusal = preference(manager, preference_name)
    if refusal:
        return {'ok': False, **refusal}
    roles = _loads(pref.role_refs_json, [])
    registered = ('MechMaterialOption'
                  in data_refs.MATERIAL_PROPERTY_CLASSES)
    result = {'ok': True, 'preference': pref.name, 'part': pref.part,
              'roles': roles, 'registered': registered, 'ids': {}}
    if not registered:
        result['warning'] = ('MechMaterialOption is not in composition.'
                             'data_refs.MATERIAL_PROPERTY_CLASSES — every '
                             'property reads as unknown')
    tiers = (('default', _loads(pref.default_ids_json, [])),
             ('alternative', _loads(pref.alternative_ids_json, [])))
    for tier, ids in tiers:
        for mid in ids:
            opt = option(manager, mid)
            if opt is None:
                result['ids'][mid] = {
                    'tier': tier, 'verdict': 'no-such-option',
                    'viable': False, 'missing_props': [],
                    'failed_predicates': [],
                    'refusal': f'no MechMaterialOption named "{mid}"'}
                continue
            v = role_viability(manager, mid, roles)
            missing = sorted({c['property'] for c in v['checks']
                              if c.get('verdict') == 'unassessed'})
            result['ids'][mid] = {
                'tier': tier, 'status': getattr(opt, 'status', ''),
                'verdict': v['verdict'],
                'viable': v['verdict'] == 'viable',
                'missing_props': missing,
                'failed_predicates': list(v['failedOn']),
                'degraded': [g['role'] + '/' + g['property']
                             for g in v['degraded']],
                'checks': v['checks'],
            }
    result['viable_ids'] = [k for k, r in result['ids'].items()
                            if r['viable']]
    result['note'] = ('every role requirement was tested on every id'
                      if all(r['verdict'] == 'viable'
                             for r in result['ids'].values())
                      else 'UNASSESSED is not a pass: a property nobody '
                           'has stated cannot clear a role requirement')
    return result


def _option_summary(opt):
    feed = _loads(getattr(opt, 'feedstocks_json', ''), [])
    return {
        'id': opt.name, 'display_name': getattr(opt, 'display_name', ''),
        'status': getattr(opt, 'status', ''),
        'worst_feedstock_iarc': getattr(opt, 'worst_feedstock_iarc', ''),
        'iarc_reasons': [f"{f.get('name')} [IARC {f.get('iarc')}]"
                         + (f" — {f['note']}" if f.get('note') else '')
                         for f in feed
                         if f.get('iarc') not in ('none', '3')],
        'caveats': _loads(getattr(opt, 'caveats_json', ''), []),
        'replaced_by': _loads(getattr(opt, 'replaced_by_json', ''), []),
        'confidence': getattr(opt, 'confidence', ''),
        'end_of_life': getattr(opt, 'end_of_life', ''),
    }


def legacy_comparison(manager, preference_name):
    """The legacy ids of a preference with their IARC reasons, next to
    the defaults (and alternatives) — what the export report prints
    for every legacy material an assembly names."""
    pref, refusal = preference(manager, preference_name)
    if refusal:
        return {'ok': False, **refusal}
    out = {'ok': True, 'preference': pref.name, 'part': pref.part,
           'defaults': [], 'alternatives': [], 'legacy': [],
           'missing': []}
    for tier, key in (('defaults', 'default_ids_json'),
                      ('alternatives', 'alternative_ids_json'),
                      ('legacy', 'legacy_ids_json')):
        for mid in _loads(getattr(pref, key, ''), []):
            opt = option(manager, mid)
            if opt is None:
                out['missing'].append(mid)
                continue
            s = _option_summary(opt)
            if tier == 'legacy':
                s['reason'] = ('; '.join(s['iarc_reasons'])
                               or '; '.join(s['caveats'])
                               or getattr(opt, 'end_of_life', '')
                               or 'legacy_harmful per the registry')
                s['polari_replacements'] = [
                    r for r in s['replaced_by']
                    if option(manager, r) is not None]
            out[tier].append(s)
    out['legacy_combinations'] = _loads(
        getattr(pref, 'legacy_harmful_json', ''), [])
    out['default_combinations'] = _loads(
        getattr(pref, 'polari_default_json', ''), [])
    out['note'] = ('IARC rows are from knowledge, not yet checked against '
                   'the monographs; rows with confidence=check first')
    return out


def density(manager, material_id):
    """(kg/m3, provenance) through composition's lookup — the one
    number the mass/dynamics side asks for most."""
    return material_prop(manager, material_id, 'density_kg_m3')

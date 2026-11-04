"""
@module mech.custom.compatibility

mxc-1: COMPATIBILITY IS A LOOKUP, NOT CODE PER FAMILY (plan §3.2). Two
MechFeatures pair when their `key` is equal and their roles form one of
ROLE_PAIRS; the joint's DOF (mxc-2) must then lie inside the
intersection of both features' dof_free. A 20-series sliding T-nut
('slot-B6/20' rider + 'M5x0.8' female) in a 2020 slot ('slot-B6/20'
channel) taking an ISO 4762 M5 ('M5x0.8' male): two pairings, both
valid by lookup; an M6 nut ('slot-B8/30' rider) in that slot is refused
by its key, with the two keys in the reason.

Thread engagement (plan §4 row mxc-2, carried here as the NAMED rule so
mxc-1 can already report it): the female side must offer at least
ENGAGEMENT_FACTORS[material class] * d of thread —
  1.0 * d steel, 2.0 * d aluminium, 2.5 * d plastic — ALL KNOBS.
check_pairing reports the engagement verdict beside the lookup verdict
and does not fold it into `ok`: a 4.7 mm M5 nut (ISO 4032 m = 4.7, the
sliding T-nut 4.7) sits BELOW 1.0 * d = 5.0 by that knob although nuts
are designed to carry the bolt at 0.8 d; the stack-aware fit check with
the screw length is mxc-2's (custom/fit_checks.py), and it decides.

Rows are read from `mgr.objectTables[<class>]` ({name: row}) — the same
shape the server and the selftest's SimpleNamespace manager give.

@consumers mech.mech_catalog_selftest, mech (mxc-2 fit checks / joints)
"""
import json

#: (role_a, role_b) pairs that mate; symmetric (both orders accepted).
ROLE_PAIRS = (('male', 'female'), ('rider', 'channel'), ('cell', 'cell'),
              ('socket', 'male'), ('plane', 'plane'))

#: Required thread engagement as a multiple of the nominal diameter d,
#: per material class of the FEMALE side — knobs, named (plan mxc-2).
ENGAGEMENT_FACTORS = {'steel': 1.0, 'aluminium': 2.0, 'plastic': 2.5}
ENGAGEMENT_BASIS = 'knob'

#: materials_registry id -> engagement material class. Coatings
#: (zinc_trivalent, black_oxide, anodise...) are not materials and map
#: to nothing; soft metals (brass, zinc alloy, die-cast) take the
#: aluminium class.
MATERIAL_CLASS = {
    'steel_carbon': 'steel', 'stainless_a2_a4': 'steel',
    'al_6063': 'aluminium', 'al_6061': 'aluminium', 'al_diecast': 'aluminium',
    'brass_lead_free': 'aluminium', 'brass_leaded': 'aluminium',
    'zinc_alloy': 'aluminium',
    'pla': 'plastic', 'petg': 'plastic', 'pp': 'plastic', 'pa66': 'plastic',
    'pa6': 'plastic', 'pa11': 'plastic', 'abs': 'plastic', 'pom': 'plastic',
    'peek': 'plastic', 'uhmwpe': 'plastic', 'pc_bpa': 'plastic',
    'pvc': 'plastic', 'ptfe': 'plastic', 'tpu_mdi': 'plastic',
    'tpu_tdi': 'plastic', 'tpc_et': 'plastic',
}


def _get(row, field, default=None):
    if isinstance(row, dict):
        return row.get(field, default)
    return getattr(row, field, default)


def _json(row, field, default):
    raw = _get(row, field, None)
    if raw in (None, ''):
        return default
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return default
    return raw


def _table(mgr, cls):
    tables = getattr(mgr, 'objectTables', None) or {}
    return tables.get(cls, {}) or {}


def roles_pair(role_a, role_b):
    return (role_a, role_b) in ROLE_PAIRS or (role_b, role_a) in ROLE_PAIRS


def pairing_reason(fa, fb):
    """'' when the two features pair; otherwise why not, naming both
    keys / roles so the refusal can be read without the rows."""
    ka, kb = _get(fa, 'key', ''), _get(fb, 'key', '')
    ra, rb = _get(fa, 'role', ''), _get(fb, 'role', '')
    if not ka or not kb:
        return 'a feature has no key (%r vs %r)' % (ka, kb)
    if ka != kb:
        return 'key mismatch: %s (%s) vs %s (%s)' % (ka, ra, kb, rb)
    if not roles_pair(ra, rb):
        return 'roles do not pair on key %s: %s vs %s (pairs: %s)' % (
            ka, ra, rb, ', '.join('%s<->%s' % p for p in ROLE_PAIRS))
    return ''


def features_compatible(fa, fb):
    """True when key equal and roles pair. Rows or dicts."""
    return pairing_reason(fa, fb) == ''


def dof_common(fa, fb):
    a = _json(fa, 'dof_free_json', [])
    b = _json(fb, 'dof_free_json', [])
    return [d for d in ('tx', 'ty', 'tz', 'rx', 'ry', 'rz') if d in a and d in b]


def material_class_for(mgr, variant_name):
    """The engagement class of a variant's family DEFAULT material
    (first registry id that maps to a class), '' when none maps."""
    v = _table(mgr, 'MechPartVariant').get(variant_name)
    if v is None:
        return ''
    fam = _table(mgr, 'MechPartFamily').get(_get(v, 'family_ref', ''))
    if fam is None:
        return ''
    for mid in _json(fam, 'material_default_ids_json', []):
        if mid in MATERIAL_CLASS:
            return MATERIAL_CLASS[mid]
    return ''


def thread_engagement(d_mm, available_mm, material_class):
    """The named rule: available >= factor(material) * d. Returns
    {ok, required_mm, available_mm, factor, material_class, basis,
    reason}; ok is None (undetermined) when the class is unknown or
    the available length is not given (-1)."""
    factor = ENGAGEMENT_FACTORS.get(material_class)
    out = {'d_mm': d_mm, 'available_mm': available_mm,
           'material_class': material_class or '',
           'factor': factor, 'basis': ENGAGEMENT_BASIS}
    if factor is None:
        out.update(ok=None, required_mm=-1,
                   reason='material class %r has no engagement factor '
                          '(knobs: %s)' % (material_class, ENGAGEMENT_FACTORS))
        return out
    required = factor * float(d_mm)
    out['required_mm'] = round(required, 3)
    if available_mm is None or available_mm < 0:
        out.update(ok=None, reason='engagement available not given (-1)')
        return out
    ok = float(available_mm) + 1e-9 >= required
    out['ok'] = ok
    out['reason'] = ('' if ok else
                     'engagement %.3g mm < %.3g mm (%.2g x d%.3g, %s, %s)' % (
                         available_mm, required, factor, d_mm,
                         material_class, ENGAGEMENT_BASIS))
    return out


def _engagement_for(mgr, fa, fb, va, vb):
    """When one side is a male thread and the other a female thread,
    the engagement report for the female side; else None."""
    pair = {_get(fa, 'role'): (fa, va), _get(fb, 'role'): (fb, vb)}
    if 'male' not in pair or 'female' not in pair:
        return None
    if _get(pair['male'][0], 'kind') != 'thread' or _get(pair['female'][0], 'kind') != 'thread':
        return None
    female, fv = pair['female']
    male, _mv = pair['male']
    fd = _json(female, 'dims_json', {})
    md = _json(male, 'dims_json', {})
    d = fd.get('d', md.get('d', -1))
    available = fd.get('engagement_available_mm', _get(female, 'extent_mm', -1))
    # the male can only engage what thread it has
    male_len = md.get('thread_length', _get(male, 'extent_mm', -1))
    if male_len is not None and male_len >= 0 and available is not None and available >= 0:
        available = min(available, male_len)
    return thread_engagement(d, available, material_class_for(mgr, fv))


def _feature(mgr, variant_name, feature_name):
    feats = _table(mgr, 'MechFeature')
    f = feats.get('%s:%s' % (variant_name, feature_name))
    if f is None:
        f = feats.get(feature_name)
    return f


def check_pairing(mgr, variant_a, feature_a, variant_b, feature_b):
    """{ok, reason, key, roles, kinds, dof_common, engagement}. A
    feature may be given by full name ('<variant>:<tag>') or by tag.
    `ok` is the lookup verdict (key equal + roles pair); `engagement`
    is reported beside it for thread pairs (see module docstring)."""
    fa = _feature(mgr, variant_a, feature_a)
    fb = _feature(mgr, variant_b, feature_b)
    out = {'variantA': variant_a, 'featureA': feature_a,
           'variantB': variant_b, 'featureB': feature_b}
    missing = [n for n, f in ((feature_a, fa), (feature_b, fb)) if f is None]
    if missing:
        out.update(ok=False, reason='unknown feature(s): %s' % ', '.join(missing))
        return out
    for f, v in ((fa, variant_a), (fb, variant_b)):
        if _get(f, 'variant_ref') != v:
            out.update(ok=False, reason='feature %s belongs to %s, not %s' % (
                _get(f, 'name'), _get(f, 'variant_ref'), v))
            return out
    reason = pairing_reason(fa, fb)
    out.update(
        ok=reason == '', reason=reason,
        key=_get(fa, 'key'), roles=[_get(fa, 'role'), _get(fb, 'role')],
        kinds=[_get(fa, 'kind'), _get(fb, 'kind')],
        dofCommon=dof_common(fa, fb),
        engagement=_engagement_for(mgr, fa, fb, variant_a, variant_b) if reason == '' else None,
    )
    return out


def pairings_for(mgr, variant_name, include_self=False):
    """Every feature of the variant -> the catalogue features it pairs
    with, grouped by variant: {feature: {variant: [feature names]}}.
    Self-pairings (a bin's lip with its own base) are left out unless
    asked for."""
    feats = _table(mgr, 'MechFeature')
    mine = [f for f in feats.values() if _get(f, 'variant_ref') == variant_name]
    by_key = {}
    for f in feats.values():
        by_key.setdefault(_get(f, 'key'), []).append(f)
    out = {}
    for f in mine:
        hits = {}
        for g in by_key.get(_get(f, 'key'), []):
            gv = _get(g, 'variant_ref')
            if gv == variant_name and not include_self:
                continue
            if roles_pair(_get(f, 'role'), _get(g, 'role')):
                hits.setdefault(gv, []).append(_get(g, 'name'))
        out[_get(f, 'name')] = hits
    return out

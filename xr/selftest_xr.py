"""
Selftest for the xr-1 cascade (settings rows + resolution + variants
preservation + the resolve API). Stdlib-only, fake manager — no DB or
server needed.

Run from the framework root:
    python3 -m xr.selftest_xr
"""

import json
import types

from xr.xr_settings import (
    XrGlobalSettings, XrTypeDefault, XrInterfaceVariant,
    SEED_XR_GLOBAL_SETTINGS, SEED_XR_TYPE_DEFAULTS,
    XR_GLOBAL_SETTINGS_NAME, variant_name, xr_global_settings_row,
)
from xr.xr_resolution import (
    BUILTIN_FRAMING, BUILTIN_MODE, effective_category, resolve_for_space,
    resolve_ladder,
)
from xr.xr_api import XrAPI

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}'
          + (f' — {extra}' if extra and not cond else ''))


def _mgr(**tables):
    base = {'XrGlobalSettings': {}, 'XrTypeDefault': {},
            'XrInterfaceVariant': {}, 'SimSpaceDefinition': {},
            'MultiScaleSimulationDefinition': {}}
    base.update(tables)
    return types.SimpleNamespace(
        objectTables=base,
        objectTypingDict={},
        idList=[],
        db=types.SimpleNamespace(saveInstanceInDB=lambda row: None))


def _space(name, category='', owning_module='', xr_mode='unset',
           xr_framing='unset'):
    return types.SimpleNamespace(
        name=name, category=category, owning_module=owning_module,
        xr_mode=xr_mode, xr_framing=xr_framing)


def _msim(name, xr_mode='unset', xr_framing='unset'):
    return types.SimpleNamespace(
        name=name, xr_mode=xr_mode, xr_framing=xr_framing)


def _seed(mgr, class_name, rows):
    table = mgr.objectTables[class_name]
    for i, row in enumerate(rows):
        table[f'{class_name}-{i}'] = row


def _fake_request(params):
    return types.SimpleNamespace(get_param=lambda key: params.get(key))


def _fake_response():
    return types.SimpleNamespace(status='200 OK', media=None)


def main():
    # ---- 1. ladder primitive ----------------------------------------
    check('ladder: all unset -> builtin',
          resolve_ladder(builtin='none') == ('none', 'builtin'))
    check('ladder: global only',
          resolve_ladder(global_value='vr', builtin='none')
          == ('vr', 'global'))
    check('ladder: type beats global',
          resolve_ladder(type_default='ar', global_value='vr',
                         builtin='none') == ('ar', 'type'))
    check('ladder: multiscale beats type+global',
          resolve_ladder(multiscale='both', type_default='ar',
                         global_value='vr', builtin='none')
          == ('both', 'multiscale'))
    check('ladder: individual beats everything',
          resolve_ladder(individual='none', multiscale='both',
                         type_default='ar', global_value='vr',
                         builtin='x') == ('none', 'individual'))
    check("ladder: '' counts as unset",
          resolve_ladder(individual='', type_default='vr',
                         builtin='none') == ('vr', 'type'))

    # ---- 2. category derivation (Q1b) --------------------------------
    check('category: explicit wins over module',
          effective_category(_space('s', category='hydroponics-layout',
                                    owning_module='aquaponics'))
          == ('hydroponics-layout', 'explicit'))
    check('category: module-derived default',
          effective_category(_space('s', owning_module='aquaponics'))
          == ('aquaponics', 'module'))
    check('category: none when neither set',
          effective_category(_space('s')) == ('', 'none'))

    # ---- 3. full resolution at every level ---------------------------
    mgr = _mgr()
    _seed(mgr, 'XrTypeDefault',
          [XrTypeDefault(category='msim-world', xr_mode='vr',
                         xr_framing='exhibit',
                         name='xr-type-msim-world')])
    _seed(mgr, 'SimSpaceDefinition', [
        _space('bare'),
        _space('typed', category='msim-world'),
        _space('pinned', category='msim-world', xr_mode='none'),
        _space('framed', xr_framing='inside'),
    ])
    _seed(mgr, 'MultiScaleSimulationDefinition',
          [_msim('wax-msim', xr_mode='both')])

    r = resolve_for_space(mgr, 'bare')
    check('resolve: whole ladder unset -> builtin none',
          r['mode'] == BUILTIN_MODE and r['modeResolvedFrom'] == 'builtin')
    check('resolve: builtin framing exhibit',
          r['framing'] == BUILTIN_FRAMING
          and r['framingResolvedFrom'] == 'builtin')

    r = resolve_for_space(mgr, 'typed')
    check('resolve: type level via category',
          r['mode'] == 'vr' and r['modeResolvedFrom'] == 'type')
    check('resolve: category provenance rides along',
          r['category'] == 'msim-world'
          and r['categorySource'] == 'explicit')

    r = resolve_for_space(mgr, 'typed', 'wax-msim')
    check('resolve: multiscale context beats type',
          r['mode'] == 'both' and r['modeResolvedFrom'] == 'multiscale')

    r = resolve_for_space(mgr, 'pinned', 'wax-msim')
    check('resolve: individual beats multiscale (direct-lower wins)',
          r['mode'] == 'none' and r['modeResolvedFrom'] == 'individual')

    # Global level: set global -> the bare space now resolves there.
    glob = xr_global_settings_row(mgr)
    check('singleton: created on first ask',
          getattr(glob, 'name', '') == XR_GLOBAL_SETTINGS_NAME)
    check('singleton: second ask returns the same row',
          xr_global_settings_row(mgr) is glob)
    glob.xr_mode = 'vr'
    r = resolve_for_space(mgr, 'bare')
    check('resolve: global level',
          r['mode'] == 'vr' and r['modeResolvedFrom'] == 'global')

    # ---- 4. global-none-except-chosen falls out of the ladder --------
    glob.xr_mode = 'none'
    r_bare = resolve_for_space(mgr, 'bare')
    r_typed = resolve_for_space(mgr, 'typed')
    r_chosen = resolve_for_space(
        mgr, 'framed')  # framed has no mode set anywhere below global
    check('global-none: unchosen spaces are none',
          r_bare['mode'] == 'none' and r_bare['modeResolvedFrom'] == 'global'
          and r_chosen['mode'] == 'none')
    check('global-none: type-set space still resolves at type '
          '(lower beats higher)',
          r_typed['mode'] == 'vr' and r_typed['modeResolvedFrom'] == 'type')
    # Explicitly choose one space back on.
    mgr.objectTables['SimSpaceDefinition']['SimSpaceDefinition-0'] \
        .xr_mode = 'vr'
    r_bare = resolve_for_space(mgr, 'bare')
    check('global-none-except-chosen: individually chosen space is vr',
          r_bare['mode'] == 'vr'
          and r_bare['modeResolvedFrom'] == 'individual')

    # Framing resolves independently of mode.
    r = resolve_for_space(mgr, 'framed')
    check('resolve: framing individual level independent of mode',
          r['framing'] == 'inside'
          and r['framingResolvedFrom'] == 'individual')

    # ---- 5. variants survive every settings flip ----------------------
    variants = [
        XrInterfaceVariant(
            name=variant_name('sim-space', 'typed', m), mode=m,
            subject_kind='sim-space', subject_name='typed',
            config_json=json.dumps({'panels': [m, 1, 2]}),
            notes=f'authored-{m}')
        for m in ('flat', 'vr', 'ar')
    ]
    _seed(mgr, 'XrInterfaceVariant', variants)
    before = [(v.name, v.mode, v.config_json, v.notes) for v in variants]
    type_row = mgr.objectTables['XrTypeDefault']['XrTypeDefault-0']
    space_row = mgr.objectTables['SimSpaceDefinition']['SimSpaceDefinition-1']
    for value in ('none', 'vr', 'ar', 'both', 'unset'):
        glob.xr_mode = value
        type_row.xr_mode = value
        space_row.xr_mode = value
        resolve_for_space(mgr, 'typed', 'wax-msim')
    for value in ('inside', 'exhibit', 'unset'):
        glob.xr_framing = value
        space_row.xr_framing = value
        resolve_for_space(mgr, 'typed')
    after = [(v.name, v.mode, v.config_json, v.notes) for v in variants]
    check('variants: byte-identical after full settings sweep',
          before == after)
    check('variants: still all present',
          len(mgr.objectTables['XrInterfaceVariant']) == 3)

    # ---- 6. the resolve API (handler level) ---------------------------
    api = XrAPI(polServer=None, manager=mgr)
    resp = _fake_response()
    api.on_get_resolve(_fake_request({'space': 'typed'}), resp)
    check('api: ok resolution payload',
          resp.media and resp.media.get('ok')
          and resp.media['resolution']['modeResolvedFrom'] in
          ('individual', 'multiscale', 'type', 'global', 'builtin'))
    resp = _fake_response()
    api.on_get_resolve(_fake_request({}), resp)
    check('api: missing space refused 400',
          resp.status.startswith('400') and not resp.media.get('ok'))
    resp = _fake_response()
    api.on_get_resolve(_fake_request({'space': 'nope'}), resp)
    check('api: unknown space 404',
          resp.status.startswith('404'))
    resp = _fake_response()
    api.on_get_resolve(
        _fake_request({'space': 'typed', 'multiscale': 'nope'}), resp)
    check('api: unknown multiscale 404',
          resp.status.startswith('404'))

    # ---- 7. seeds are shaped right ------------------------------------
    check('seeds: one global row seed, named',
          len(SEED_XR_GLOBAL_SETTINGS) == 1
          and SEED_XR_GLOBAL_SETTINGS[0]['name'] == XR_GLOBAL_SETTINGS_NAME)
    check('seeds: type defaults carry category + named rows',
          all(s.get('name') and s.get('category')
              for s in SEED_XR_TYPE_DEFAULTS))
    check('seeds: Q9 — hydroponics-layout ar/inside, msim-world '
          'vr/exhibit',
          any(s['category'] == 'hydroponics-layout'
              and s['xr_mode'] == 'ar' and s['xr_framing'] == 'inside'
              for s in SEED_XR_TYPE_DEFAULTS)
          and any(s['category'] == 'msim-world' and s['xr_mode'] == 'vr'
                  and s['xr_framing'] == 'exhibit'
                  for s in SEED_XR_TYPE_DEFAULTS))

    failures = [label for label, ok in _results if not ok]
    print(f'\n{len(_results) - len(failures)}/{len(_results)} checks passed')
    if failures:
        print('FAILED: ' + ', '.join(failures))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()

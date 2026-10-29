"""
@module cmod.custom.bench_structs

hsp-3b (HARDWARE_SYSTEM_PINS_PLAN.md §7 "The two bench views", his words 2026-10-28: "click on specific struct instances on the hardware, and then fields in
that struct, and be able to have from assertions where the signals pass through that change those pieces of the struct from catoms"): the rows the Structs
and Bridges views draw. Everything is DERIVED - no new stored row:

  struct instance = a bench bridge (PolariBridgeInstance: its `bridge_definition` names the firmware variant, its `maps` the StructObjectMaps)
                    x a HardwareInterfaceBinding of that variant whose object class is the map's Polari class (instance_index = the struct's index, object_name =
                    the Polari object it becomes once it crosses). A map with no binding is still an instance (index 0), said unbound.
  instances(bench)              -> one row per struct instance on the bench (the Structs view's cards; filter `bridge` = the Bridges view's "crossing" list)
  fields(bench, instance)       -> one row per field: the Polari attribute, the catoms that change / read it (from the Catom assertions), the pins, the verdict
  path(bench, instance, field)  -> the signal paths that change the field, as ordered hop rows: pin -> catom -> field -> catom -> bridge -> object attribute
                                   (reads-field: field -> catom -> pin); unverified / false assertions keep their status; a field nothing asserts = one gap row
"""
from cmod.custom import catom_assertions as CA

VIEWS = ('instances', 'fields', 'path')
_ORDER = {'verified': 0, 'unverified': 1, 'false': 2, 'gap': 3}


def _get(o, k, d=''):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _bindings(rows):
    if rows is not None:
        return [{k: _get(r, k) for k in ('name', 'bridge_name', 'object_class', 'object_name', 'instance_index')} for r in rows]
    try:
        from hwnocode.custom.light_solutions import binding_row
        return [binding_row()]
    except Exception:  # noqa: BLE001 - the seeds' own binding; a host without hwnocode simply has none
        return []


def _bridges(bench, bridge_rows, path_rows):
    from grpcbridge.custom import bridge_paths as BP
    return BP.bench_bridges(bench, bridge_rows, path_rows)['bridges']


def instances(bench, bridge_rows=None, path_rows=None, binding_rows=None, map_rows=None, assertion_rows=None, bridge=''):
    maps = {}
    for m in CA.map_rows(map_rows):
        maps.setdefault(m['map'], m)
    binds = _bindings(binding_rows)
    out = []
    for b in _bridges(bench, bridge_rows, path_rows):
        if bridge and b['name'] != bridge:
            continue
        variant = b['bridge_definition']
        asserted = CA.assertions(variant, assertion_rows) if variant else []
        for mname in [x.strip() for x in (b['maps'] or '').split(',') if x.strip()]:
            m = maps.get(mname)
            if m is None:
                out.append({'name': '%s/%s' % (b['name'], mname), 'bench': bench, 'bridge': b['name'], 'hardware_id': b['hardware_id'], 'variant': variant,
                            'struct': '', 'index': 0, 'polari_class': '', 'object': '', 'binding': '', 'pins': '', 'fields': 0, 'asserted_fields': 0,
                            'verified': 0, 'state': 'gap', 'why': 'the bridge names StructObjectMap %r, which does not exist' % mname})
                continue
            mine = [a for a in asserted if a['struct'] == m['struct']]
            fields = [r['field'] for r in CA.map_rows(map_rows) if r['map'] == mname]
            touched = {f for a in mine if a['kind'] in ('changes-field', 'reads-field') for f in CA._fields_of(a)}
            pins = sorted({p for a in mine for p in (a['pins'] or '').split(',') if p})
            hits = sorted((x for x in binds if x['bridge_name'] == variant and x['object_class'] == m['polari_class']), key=lambda x: int(x['instance_index'] or 0))
            for x in hits or [None]:
                idx = int(x['instance_index'] or 0) if x else 0
                out.append({'name': '%s/%s[%d]' % (b['name'], m['struct'], idx), 'bench': bench, 'bridge': b['name'], 'hardware_id': b['hardware_id'], 'variant': variant,
                            'struct': m['struct'], 'index': idx, 'polari_class': m['polari_class'], 'object': x['object_name'] if x else '',
                            'binding': x['name'] if x else '', 'pins': ','.join(pins), 'fields': len(fields), 'asserted_fields': len(touched & set(fields)),
                            'verified': sum(a['status'] == 'verified' for a in mine), 'state': 'bound' if x else 'unbound',
                            'why': ('crosses %s as %s %r (HardwareInterfaceBinding %s)' % (b['name'], m['polari_class'], x['object_name'], x['name']) if x else
                                    'no HardwareInterfaceBinding of %s carries %s: the struct has no Polari object yet' % (variant, m['polari_class']))})
    return out


def _instance(bench, name, **rows):
    return next((i for i in instances(bench, **rows) if i['name'] == name), None)


def fields(bench, instance, **rows):
    inst = _instance(bench, instance, **rows)
    if inst is None:
        return None
    mine = [a for a in CA.assertions(inst['variant'], rows.get('assertion_rows')) if a['struct'] == inst['struct']]
    out = []
    for r in [r for r in CA.map_rows(rows.get('map_rows')) if r['struct'] == inst['struct'] and r['polari_class'] == inst['polari_class']]:
        ch = [a for a in mine if a['kind'] == 'changes-field' and r['field'] in CA._fields_of(a)]
        rd = [a for a in mine if a['kind'] == 'reads-field' and r['field'] in CA._fields_of(a)]
        sts = [a['status'] for a in ch + rd]
        out.append({'instance': instance, 'field': r['field'], 'attribute': '%s.%s' % (inst['polari_class'], r['attribute']),
                    'changed_by': ', '.join(CA._short(a['atom']) for a in ch) or '-', 'read_by': ', '.join(CA._short(a['atom']) for a in rd) or '-',
                    'pins': ','.join(sorted({p for a in ch + rd for p in (a['pins'] or '').split(',') if p})) or '-',
                    'verdict': max(sts, key=_ORDER.get) if sts else 'gap',
                    'why': '; '.join('%s %s: %s' % (CA._short(a['atom']), a['status'], a['status_why']) for a in ch + rd)
                           or 'no catom asserts a change or a read of %s.%s' % (inst['struct'], r['field'])})
    return out


def _step(route, n, kind, what, status, why, direction=''):
    return {'route': route, 'step': n, 'kind': kind, 'what': what, 'direction': direction, 'status': status, 'why': why}


def path(bench, instance, field, **rows):
    inst = _instance(bench, instance, **rows)
    if inst is None:
        return None
    mine = [a for a in CA.assertions(inst['variant'], rows.get('assertion_rows')) if a['struct'] == inst['struct']]
    attr = next((r['attribute'] for r in CA.map_rows(rows.get('map_rows')) if r['struct'] == inst['struct'] and r['field'] == field), '')
    if not attr:
        return []
    sends = [a for a in mine if a['kind'] == 'sends-to-bridge' and a['bridge'] == inst['bridge']]
    out, route = [], 0
    for a in [a for a in mine if a['kind'] == 'changes-field' and field in CA._fields_of(a)]:
        route += 1
        n = 0
        if a['bridge'] and a['bridge'] == inst['bridge']:
            # the change comes FROM the bridge (SET_LED from the UI): the object -> the bridge -> the receiving catom, then the pin and the changing catom
            out.append(_step(route, 1, 'object', '%s %r (the UI writes .%s)' % (inst['polari_class'], inst['object'] or '(no object)', attr), inst['state'], inst['why'], 'in'))
            out.append(_step(route, 2, 'bridge', '%s (%s)' % (inst['bridge'], inst['hardware_id']), inst['state'], inst['why'], 'in'))
            n = 2
        for p in [p for p in (a['pins'] or '').split(',') if p]:
            n += 1
            out.append(_step(route, n, 'pin', '%s (%s)' % (p, a['event'] or 'signal'), a['status'], 'the signal that starts the change', 'in'))
        if a['bridge'] and a['bridge'] == inst['bridge']:
            for r in [r for r in mine if r['kind'] == 'receives-from-bridge' and r['bridge'] == inst['bridge']]:
                n += 1
                out.append(_step(route, n, 'catom', '%s [%s lane] receives the bytes' % (CA._short(r['atom']), r['lane']), r['status'], r['status_why'], 'in'))
        out.append(_step(route, n + 1, 'catom', '%s [%s lane, updater %s]' % (CA._short(a['atom']), a['lane'], a['updater'] or '-'), a['status'], a['status_why']))
        out.append(_step(route, n + 2, 'field', '%s[%d].%s' % (inst['struct'], inst['index'], field), a['status'], a['notes'] or a['basis']))
        k = n + 2
        for s in sends:
            out.append(_step(route, k + 1, 'catom', '%s [%s lane] sends the struct' % (CA._short(s['atom']), s['lane']), s['status'], s['status_why']))
            k += 1
        if sends:
            out.append(_step(route, k + 1, 'bridge', '%s (%s)' % (inst['bridge'], inst['hardware_id']), inst['state'], inst['why'], 'out'))
            out.append(_step(route, k + 2, 'object', '%s %r .%s' % (inst['polari_class'], inst['object'] or '(no object)', attr), inst['state'], inst['why']))
        else:
            out.append(_step(route, k + 1, 'gap', 'no catom asserts sends-to-bridge %s for %s' % (inst['bridge'], inst['struct']), 'gap',
                             'the change stays on the board: nothing carries it across'))
    for a in [a for a in mine if a['kind'] == 'reads-field' and field in CA._fields_of(a)]:
        route += 1
        out.append(_step(route, 1, 'field', '%s[%d].%s' % (inst['struct'], inst['index'], field), a['status'], 'read by the catom'))
        out.append(_step(route, 2, 'catom', '%s [%s lane]' % (CA._short(a['atom']), a['lane']), a['status'], a['status_why']))
        for i, p in enumerate([p for p in (a['pins'] or '').split(',') if p]):
            out.append(_step(route, 3 + i, 'pin', p, a['status'], a['notes'] or 'the field drives this pin', 'out'))
    if not out:
        out.append(_step(0, 0, 'gap', '%s[%d].%s' % (inst['struct'], inst['index'], field), 'gap', 'no catom asserts a change or a read of this field'))
    return out

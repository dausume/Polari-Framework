"""
@module suiteapps.custom.placement

Place a suite's parts across devices. Pure. Inputs are plain dicts:
  parts      [{name, app, kind, placement, same_as, node, required, order}]
  devices    [{name, is_core, hardware_tier_ready, ports_satisfy: [app names the map says it can serve],
               logical_cpus, total_ram_mb, load}]   (from HardwareMapSnapshot + PolariNodeMachine + IsleDevice)
  needs      {app: est_ram_mb}  (the coverage planner's estimate per app, optional)
Rules: a `core` part goes to the core; a `hardware` part goes to a
hardware-tier device whose map satisfies the app (else 'needs-hardware-
tier' naming what is missing); a `node` part goes to its named node if
present; `same-as` follows the part it names; `any` goes to the
least-loaded device. Every verdict carries its reason.
"""
import time


def place(parts, devices, needs=None):
    needs = needs or {}
    by_name = {d['name']: d for d in devices}
    core = next((d for d in devices if d.get('is_core')), None)
    load = {d['name']: float(d.get('load') or 0) for d in devices}
    out = {}
    stamp = time.strftime('%Y-%m-%dT%H:%M:%S')
    def take(dev, part):
        load[dev] = load.get(dev, 0) + float(needs.get(part['app'], 300)) / max(1.0, float(by_name[dev].get('total_ram_mb') or 4096))
    for part in sorted(parts, key=lambda p: (p.get('placement') == 'same-as', p.get('order', 0))):
        name, pl = part['name'], part.get('placement', 'any')
        rec = {'part': name, 'device': '', 'verdict': 'unplaceable', 'reason': '', 'computed_at': stamp}
        if not devices:
            rec['reason'] = 'no devices known (no HardwareMapSnapshot / PolariNodeMachine rows)'
        elif pl == 'core':
            if core:
                rec.update(device=core['name'], verdict='placed', reason='the core'); take(core['name'], part)
            else:
                rec['reason'] = 'no core device known'
        elif pl == 'hardware':
            ready = [d for d in devices if d.get('hardware_tier_ready')]
            fit = [d for d in ready if part['app'] in (d.get('ports_satisfy') or [])]
            if fit:
                dev = min(fit, key=lambda d: load[d['name']])
                rec.update(device=dev['name'], verdict='placed', reason='hardware tier + the map has a port satisfying %s' % part['app']); take(dev['name'], part)
            elif ready:
                rec.update(verdict='needs-hardware-tier', reason='hardware-tier devices exist (%s) but none has a mapped port satisfying %s — plug the hardware in and pol hwmap push' % (', '.join(d['name'] for d in ready), part['app']))
            else:
                rec.update(verdict='needs-hardware-tier', reason='no device is hardware-tier ready (cpu virt + /dev/kvm + libvirt); isle onboard --host --hardware on one')
        elif pl == 'node':
            if part.get('node') in by_name:
                rec.update(device=part['node'], verdict='placed', reason='pinned to node %s' % part['node']); take(part['node'], part)
            else:
                rec.update(verdict='needs-node', reason='named node %r is not known' % part.get('node'))
        elif pl == 'same-as':
            target = out.get(part.get('same_as', ''))
            if target and target['device']:
                rec.update(device=target['device'], verdict='placed', reason='same device as %s' % part['same_as']); take(target['device'], part)
            else:
                rec.update(verdict='unplaceable', reason='follows %r which is not placed' % part.get('same_as'))
        else:
            dev = min(devices, key=lambda d: load[d['name']])
            rec.update(device=dev['name'], verdict='placed', reason='least-loaded device'); take(dev['name'], part)
        out[name] = rec
    summary = {'placed': sum(1 for r in out.values() if r['verdict'] == 'placed'), 'parts': len(out),
               'devices_used': sorted({r['device'] for r in out.values() if r['device']}),
               'blocking': [r['part'] for r in out.values() if r['verdict'] != 'placed' and next((p for p in parts if p['name'] == r['part']), {}).get('required', True)]}
    return {'placements': list(out.values()), 'summary': summary}

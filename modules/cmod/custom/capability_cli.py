"""
@module cmod.custom.capability_cli

`pol capability prove <name> [--twin|--hardware]` (hw priorities P1): runs the capability's acceptance Scenario
(firmwarefaults.custom.acceptance.run) and reports the outcome. --hardware is wired to the EXISTING stopgap
flash/detect path (cmod.custom.firmware.run(mode='hardware') -> board.custom.installer.detected) — with no board
plugged in it REFUSES with the readiness reason; this CLI does not try to make it pass
(AI-Notes/plans/HARDWARE_DEV_PRIORITIES.md §3 P2: the UNO is not attached yet).

    python3 -m cmod.custom.capability_cli prove <name> [--twin|--hardware]
    python3 -m cmod.custom.capability_cli list
"""
import argparse
import sys


def cmd_prove(a):
    from cmod.custom import capabilities as CAP
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom.sink import LocalSink
    cap = CAP.find(a.name)
    if cap is None:
        print('[REFUSED] no capability %r (pol capability list)' % a.name)
        return 3
    ok, why = CAP.validate(cap)
    if not ok:
        print('[REFUSED] %s' % why)
        return 3
    mode = 'hardware' if a.hardware else 'digital-twin'
    sink = LocalSink()
    out = ACC.run(cap['acceptance_scenario'], mode=mode, sink=sink)
    tag = {'passed': '[PASS]', 'failed': '[FAIL]', 'inapplicable': '[N/A ]', 'undetermined': '[ ?? ]'}.get(out['outcome'], '[    ]')
    print('%s %s on %s (scenario %s) — %s' % (tag, a.name, mode, out['scenario'], out['verdict_words']))
    print('       record    %s' % sink.flush(out['name']))
    return 0 if out['outcome'] == 'passed' else (3 if out['outcome'] == 'inapplicable' else 1)


def cmd_list(a):
    from cmod.custom import capabilities as CAP
    for cap in CAP.SEED_CAPABILITIES:
        ok, why = CAP.validate(cap)
        status, proof, swhy = CAP.derive_status(cap)
        print('  %-20s %-20s %s' % (cap['name'], status, cap['goal']))
        print('       validator  %s' % ('ok' if ok else why))
        print('       proof      %s (%s)' % (proof or '-', swhy))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(prog='pol capability')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prove')
    p.add_argument('name')
    g = p.add_mutually_exclusive_group()
    g.add_argument('--twin', action='store_true')
    g.add_argument('--hardware', action='store_true')
    sub.add_parser('list')
    a = ap.parse_args(argv)
    return {'prove': cmd_prove, 'list': cmd_list}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

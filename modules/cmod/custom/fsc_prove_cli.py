"""
@module cmod.custom.fsc_prove_cli

fsc-6: `pol firmware prove <config> [--api URL] [--dry-run] [--json] [--mission M] [--hardware]`. A config is FINISHED when it is built and every Purpose of the Mission has a passed ScenarioRun of
THAT config's own firmware (cmod.custom.fsc_link). This verb does the whole job for one config: for each Purpose of the Mission it runs the Purpose's own acceptance scenario on the config's build
(firmwarefaults.custom.acceptance.run(..., variant=config): the twin, here, through the board engines seam), stores the run under $POLARI_FAULTS_HOME, and with --api pushes it to that server's
Purpose door (POST /api/capabilities/<purpose>/runs, body.variant = the config), then asks the server's score door whether the config now reads `finished`.

  Configs (smp-1): any built config of the Mission - the sample's S1 uno-light-sense-poll, S2 uno-light-all-pcint, S3 uno-light-pwm-analog, S4 uno-light-transistor, and uno-light-sense-pcint. Each Purpose's
  press / command is made the way THE CONFIG'S OWN button and light need (INT0, a pin-change pin, a voltage on A0).
  --dry-run   print what would run and where it would be pushed; run nothing, write nothing, push nothing
  --json      print one JSON document (config, mission, steps, outcome per Purpose, pushes, finished) instead of the lines
  Exit code 0 = every Purpose passed (and, with --api, every push was accepted); 1 = a run failed; 3 = refused (no such config / not a built config of the Mission).

    python3 -m cmod.custom.fsc_prove_cli <config> [--mission M] [--api URL] [--dry-run] [--json] [--hardware]
"""
import argparse
import json
import sys


def plan(config, mission, manager=None):
    """-> ([{purpose, scenario}], refusal). The Mission's Purposes in order, each with its OWN acceptance scenario; the refusal is '' when `config` may be proven for them."""
    from cmod.custom import approach_profile_input as AI
    from cmod.custom import capabilities as CAP
    from cmod.custom import fsc_link
    row = AI.find_mission(mission, manager)
    if row is None:
        return [], 'no Mission %r' % mission
    steps = [{'purpose': p['purpose'], 'scenario': (CAP.find(p['purpose']) or {}).get('acceptance_scenario', '')} for p in AI.purposes_of(row, manager)]
    for s in steps:
        if not s['scenario']:
            return steps, 'Purpose %s has no acceptance scenario, so nothing can prove it' % s['purpose']
        why = fsc_link.proof_config_refusal(config, s['scenario'], manager, mission)
        if why:
            return steps, why
    return steps, ''


def _finished(api, config, mission, http):
    code, d = http(api, 'GET', '/api/firmware-scores', {'mission': mission, 'scope': 'finished'})
    if code != 200:
        return None, 'the score door answered HTTP %s: %s' % (code, (d or {}).get('error', ''))
    hit = next((r for r in d.get('rows', []) if r.get('state') == 'finished' and config in (r.get('long_label'), r.get('label'), r.get('solution'))), None)
    return (hit is not None), ('the scores page lists %s as finished' % config) if hit else ('the scores page does not list %s as finished yet' % config)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='pol firmware prove')
    ap.add_argument('config')
    ap.add_argument('--mission', default='')
    ap.add_argument('--api', default='')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--hardware', action='store_true')
    a = ap.parse_args(argv)
    from cmod.custom import fsc_doors
    mission = a.mission or fsc_doors.DEFAULT_MISSION
    api = a.api.rstrip('/') or ''
    steps, refused = plan(a.config, mission)
    doc = {'config': a.config, 'mission': mission, 'api': api, 'dry_run': a.dry_run, 'steps': steps, 'refused': refused}

    def out(code):
        if a.json:
            print(json.dumps(doc, indent=1, default=str))
        return code
    if refused:
        doc['ok'] = False
        if not a.json:
            print('[REFUSED] %s' % refused)
        return out(3)
    if a.dry_run:
        doc['ok'] = True
        for s in steps:
            s['door'] = ('%s/api/capabilities/%s/runs' % (api, s['purpose'])) if api else '(not pushed: no --api)'
            if not a.json:
                print('would run  %-44s on %s  ->  %s' % (s['scenario'], a.config, s['door']))
        if not a.json:
            print('dry run: nothing run, nothing stored, nothing pushed')
        return out(0)
    from cmod.custom.fsc_cli import _remote
    from firmwarefaults.custom import acceptance as ACC
    from firmwarefaults.custom import faults_cli as FC
    from firmwarefaults.custom.sink import LocalSink
    mode = 'hardware' if a.hardware else 'digital-twin'
    all_passed, all_pushed = True, True
    for s in steps:
        sink = LocalSink()
        r = ACC.run(s['scenario'], mode=mode, sink=sink, variant=a.config)
        s.update(outcome=r['outcome'], run=r['name'], variant=r['variant'], words=r['verdict_words'], record=sink.flush(r['name']))
        all_passed = all_passed and r['outcome'] == 'passed'
        if api:
            d = FC._http('POST', '%s/api/capabilities/%s/runs' % (api, s['purpose']), {k: v for k, v in r.items() if k != 'result'})
            s['pushed'] = bool(d.get('ok'))
            s['push_note'] = 'accepted' if d.get('ok') else d.get('error', str(d))
            all_pushed = all_pushed and s['pushed']
        if not a.json:
            print('[%s] %-16s %-44s %s' % ({'passed': 'PASS', 'failed': 'FAIL', 'inapplicable': 'N/A '}.get(r['outcome'], ' ?? '), s['purpose'][:16], s['scenario'], r['verdict_words'][:150]))
            if api:
                print('       push      %s: %s' % (s['push_note'], r['name']))
    doc['ok'] = all_passed and all_pushed
    if api:
        doc['finished'], doc['finished_note'] = _finished(api, a.config, mission, _remote)
        if not a.json:
            print('finished   %s' % doc['finished_note'])
    elif not a.json:
        print('not pushed (no --api): the runs are under $POLARI_FAULTS_HOME; %s' % ('all four Purposes passed on %s' % a.config if all_passed else 'a Purpose did not pass'))
    return out(0 if doc['ok'] else 1)


if __name__ == '__main__':
    sys.exit(main())

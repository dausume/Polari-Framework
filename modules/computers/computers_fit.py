"""
@module computers.computers_fit

cmp-c-3: profile fit as the ai-6 hosting-gauge verdict ladder
applied to a BUILD instead of a live machine — a profile is a
declared requirements floor, an assembly either clears every
floor, misses one (with the failing numbers quoted), or the floor
is UNANSWERABLE because the build never declared the spec
('unverified', never rounded up to a yes).

Floors vocabulary (floors_json): cores, ram_mb, disk_mb, vram_mb
(ints, 0/absent = no floor), gpu_required, fpga_required (bools).
gpu_required is answered by the build's gpu part or declared
vram_mb; fpga_required by an 'fpga-accelerator' part in the parts
list — presence checks, honest about what they do not measure
(a dev-board FPGA satisfies fpga_required; whether its interface
suits the workload is the taxonomy row's gaps_note, not a silent
assumption).

@consumers
  - computers.computers_api (fit payloads)
  - computers.selftest_computers
"""

import json

from computers.computers_basis import field_of


def _loads(row, field, default):
    try:
        return json.loads(field_of(row, field, default) or default)
    except ValueError:
        return json.loads(default)


def fit_profile(profile, build, parts_by_name):
    """Score one build against one profile. Pure. Returns
    per-floor verdicts ('yes' | 'no' | 'unverified') + an overall
    verdict that is 'fit' only when every DECLARED floor answered
    yes and nothing required stayed unverified."""
    floors = _loads(profile, 'floors_json', '{}')
    specs = _loads(build, 'specs_json', '{}')
    part_names = _loads(build, 'parts_json', '[]')
    parts = [parts_by_name[n] for n in part_names
             if n in parts_by_name]
    kinds = [field_of(p, 'kind') for p in parts]
    verdicts = []

    def add(req, verdict, detail):
        verdicts.append({'requirement': req, 'verdict': verdict,
                         'detail': detail})

    for key, label in (('cores', 'cores'), ('ram_mb', 'RAM MB'),
                       ('disk_mb', 'disk MB'),
                       ('vram_mb', 'VRAM MB')):
        need = int(floors.get(key, 0) or 0)
        if not need:
            continue
        have = specs.get(key)
        if have is None:
            add(key, 'unverified',
                '%s floor %d declared but the build does not '
                'declare %s' % (label, need, key))
        elif int(have) >= need:
            add(key, 'yes', '%d >= %d needed' % (int(have), need))
        else:
            add(key, 'no', '%s: %d < %d needed'
                % (label, int(have), need))

    if floors.get('gpu_required'):
        if 'gpu' in kinds or specs.get('vram_mb'):
            add('gpu_required', 'yes',
                'gpu part present' if 'gpu' in kinds
                else 'vram_mb declared on the build')
        else:
            add('gpu_required', 'no', 'no gpu part in the build')
    if floors.get('fpga_required'):
        if 'fpga-accelerator' in kinds:
            fpga = next(p for p in parts
                        if field_of(p, 'kind') == 'fpga-accelerator')
            add('fpga_required', 'yes',
                '%s present (presence check only — interface '
                'suitability is the taxonomy gaps_note)'
                % field_of(fpga, 'name'))
        else:
            add('fpga_required', 'no',
                'no fpga-accelerator part in the build')

    misses = [v for v in verdicts if v['verdict'] == 'no']
    unknown = [v for v in verdicts if v['verdict'] == 'unverified']
    if not verdicts:
        overall, note = 'unverified', \
            'the profile declares no floors — nothing to score'
    elif misses:
        overall = 'no-fit'
        note = 'floor missed: ' + '; '.join(m['detail']
                                            for m in misses)
    elif unknown:
        overall = 'unverified'
        note = ('no floor missed, but %d floor(s) unanswerable — '
                'declare the spec(s) on the build to finish the '
                'verdict' % len(unknown))
    else:
        overall = 'fit'
        note = 'every declared floor clears'
    result = {
        'profile': field_of(profile, 'name'),
        'build': field_of(build, 'name'),
        'verdicts': verdicts,
        'overall': overall,
        'note': note,
        'planner_class': field_of(profile, 'planner_class'),
    }
    if field_of(profile, 'db_binding') == 'declare':
        result['db_binding'] = {
            'mode': 'declare-only',
            'db_ref': field_of(profile, 'db_ref'),
            'note': 'residence intent recorded — real topology '
                    'hooks are the object-ownership arc '
                    '(decision 3, declare-only v1)',
        }
    return result


def fit_matrix(profiles, builds, parts_by_name):
    """Every published profile x build — the catalog payload."""
    out = []
    for prof in profiles:
        if not field_of(prof, 'published', True):
            continue
        row = {'profile': field_of(prof, 'name'),
               'display_name': field_of(prof, 'display_name'),
               'fits': []}
        for build in builds:
            if not field_of(build, 'published', True):
                continue
            fit = fit_profile(prof, build, parts_by_name)
            row['fits'].append({'build': fit['build'],
                                'overall': fit['overall']})
        out.append(row)
    return out

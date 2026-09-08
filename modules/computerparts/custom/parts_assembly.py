"""
@module computerparts.custom.parts_assembly

ai-8b (Dustin: "we should be able to track assembly feasibility
and performance between parts"): assembly feasibility as DERIVED
CHECKS over declared part specs — never folklore. Each check
verdict is 'ok' | 'mismatch' | 'unverified':

  socket        cpu.socket == motherboard.socket
  ram-type      ram.ram_type == motherboard.ram_type
  psu-wattage   psu.watts >= gpu.watts + platform draw + headroom
  gpu-clearance gpu.length_mm <= case.max_gpu_length_mm

A spec nobody declared yields 'unverified — <spec> not declared',
which is the honest answer and also the affordance: declare it on
the part row and the check starts answering. PERFORMANCE between
parts (bottleneck modeling) is deliberately NOT modeled here —
that needs measured benchmarks as rows, not guesses; when it
lands it is its own concern (possibly its own module).

@consumers
  - computerparts.parts_api (build payloads)
  - appstore.appstore_ai_api (buy-vs-rent join)
  - computerparts.computerparts_selftest
"""

import json

#: Non-GPU platform draw estimate + safety headroom for the PSU
#: check (researched rule of thumb: size the PSU well above the
#: GPU's board power; stated in the check detail).
PLATFORM_DRAW_W = 150
PSU_HEADROOM = 1.25


def _specs(part):
    if part is None:
        return {}
    raw = part.get('specs_json', '{}') if isinstance(part, dict) \
        else getattr(part, 'specs_json', '{}')
    try:
        return json.loads(raw or '{}')
    except ValueError:
        return {}


def _first_of_kind(parts, kind):
    for p in parts:
        k = p.get('kind') if isinstance(p, dict) \
            else getattr(p, 'kind', '')
        if k == kind:
            return p
    return None


def assembly_check(build, parts_by_name):
    """Derived assembly feasibility for one build. Pure. Returns
    {'checks': [{check, verdict, detail}], 'feasible': bool|None}
    — feasible True only when every ANSWERABLE check passes and at
    least one answered; None when nothing was answerable."""
    raw = build.get('parts_json', '[]') if isinstance(build, dict) \
        else getattr(build, 'parts_json', '[]')
    try:
        names = json.loads(raw or '[]')
    except ValueError:
        names = []
    parts = [parts_by_name[n] for n in names if n in parts_by_name]

    cpu = _specs(_first_of_kind(parts, 'cpu'))
    mb = _specs(_first_of_kind(parts, 'motherboard'))
    ram = _specs(_first_of_kind(parts, 'ram'))
    gpu = _specs(_first_of_kind(parts, 'gpu'))
    psu = _specs(_first_of_kind(parts, 'psu'))
    case = _specs(_first_of_kind(parts, 'case'))

    checks = []

    def add(check, verdict, detail):
        checks.append({'check': check, 'verdict': verdict,
                       'detail': detail})

    # socket: cpu <-> motherboard
    if cpu.get('socket') and mb.get('socket'):
        ok = cpu['socket'] == mb['socket']
        add('socket', 'ok' if ok else 'mismatch',
            '%s (cpu) vs %s (board)' % (cpu['socket'],
                                        mb['socket']))
    else:
        add('socket', 'unverified',
            'socket not declared on cpu and/or motherboard')

    # ram type: ram <-> motherboard
    if ram.get('ram_type') and mb.get('ram_type'):
        ok = ram['ram_type'] == mb['ram_type']
        add('ram-type', 'ok' if ok else 'mismatch',
            '%s (ram) vs %s (board)' % (ram['ram_type'],
                                        mb['ram_type']))
    else:
        add('ram-type', 'unverified',
            'ram_type not declared on ram and/or motherboard')

    # psu wattage vs gpu draw + platform + headroom
    if gpu.get('watts') and psu.get('watts'):
        need = int((gpu['watts'] + PLATFORM_DRAW_W) * PSU_HEADROOM)
        ok = psu['watts'] >= need
        add('psu-wattage', 'ok' if ok else 'mismatch',
            '%d W psu vs ~%d W needed (gpu %d + platform %d, '
            'x%.2f headroom)' % (psu['watts'], need, gpu['watts'],
                                 PLATFORM_DRAW_W, PSU_HEADROOM))
    else:
        add('psu-wattage', 'unverified',
            'watts not declared on gpu and/or psu')

    # gpu length vs case clearance
    if gpu.get('length_mm') and case.get('max_gpu_length_mm'):
        ok = gpu['length_mm'] <= case['max_gpu_length_mm']
        add('gpu-clearance', 'ok' if ok else 'mismatch',
            '%d mm gpu vs %d mm case clearance'
            % (gpu['length_mm'], case['max_gpu_length_mm']))
    else:
        add('gpu-clearance', 'unverified',
            'length_mm / max_gpu_length_mm not declared')

    answered = [c for c in checks if c['verdict'] != 'unverified']
    feasible = None
    if answered:
        feasible = all(c['verdict'] == 'ok' for c in answered)
    return {
        'checks': checks,
        'feasible': feasible,
        'note': ('all declared checks pass — undeclared specs '
                 'stay unverified' if feasible else
                 'a declared check MISMATCHES — see checks'
                 if feasible is False else
                 'no compat specs declared yet — declare socket/'
                 'ram_type/watts on the part rows to start '
                 'answering'),
    }

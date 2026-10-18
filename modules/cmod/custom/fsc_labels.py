"""
@module cmod.custom.fsc_labels

fsc-3: SHORT LABELS for solutions - what a table row or a chart axis shows instead of the long route string
("drive-led:gpio-out, read-button:ext-interrupt, ..."): e.g. `button ext-int · sense poll · LED out · UNO`.

Only the jobs that VARY across the compared plans are named (a job with one possible route, such as the UART transport, is the same in every plan and would only add noise);
the board closes the label. Words are plain; an unknown job or route falls back to its own name, so nothing is ever dropped or invented. The long route string stays in the
`routes` field and in the breakdown.
"""
JOB_WORD = {'read-button': 'button', 'sense-led-line': 'sense', 'drive-led': 'LED', 'receive-command': 'command in', 'report-state': 'report'}
ROUTE_WORD = {'gpio-poll': 'poll', 'gpio-out': 'out', 'ext-interrupt': 'ext-int', 'pin-change-interrupt': 'pin-change', 'analog-comparator': 'comparator',
              'analog-threshold': 'threshold', 'analog-read': 'analog', 'i2c-expander': 'I2C expander', 'spi-shift-register': 'SPI shift reg', 'transistor-switch': 'transistor',
              'pwm': 'PWM', 'uart-rx-interrupt': 'UART rx', 'uart-tx': 'UART tx'}
TIER_WORD = {'bare-c': 'bare C', 'freertos': 'FreeRTOS', 'zephyr': 'Zephyr'}
BOARD_WORD = {'arduino-uno-r3': 'UNO', 'esp32-c3': 'ESP32-C3'}


def varying_jobs(candidates):
    """The jobs that take more than one route among the candidates, in first-seen order."""
    seen = {}
    for c in candidates:
        for job, route in c['routes'].items():
            seen.setdefault(job, set()).add(route)
    return [j for j, rs in seen.items() if len(rs) > 1]


def tiers_vary(candidates):
    """True when the candidates run at more than one runtime tier (the tier is then part of the label)."""
    return len({c.get('tier') for c in candidates}) > 1


def short_label(candidate, jobs, with_tier=False):
    """`<job word> <route word> · ... · <board word> [<tier word>]` over the varying `jobs` (all jobs when none vary); the tier only when tiers vary."""
    routes = candidate['routes']
    order = list(JOB_WORD)
    names = sorted([j for j in (jobs or list(routes)) if j in routes], key=lambda j: order.index(j) if j in order else len(order))
    parts = ['%s %s' % (JOB_WORD.get(j, j), ROUTE_WORD.get(routes[j], routes[j])) for j in names]
    board = (candidate.get('hardware') or {}).get('board', '')
    parts.append(('%s %s' % (BOARD_WORD.get(board, board), TIER_WORD.get(candidate.get('tier'), candidate.get('tier') or ''))).strip() if with_tier else BOARD_WORD.get(board, board))
    return ' · '.join(p for p in parts if p.strip())

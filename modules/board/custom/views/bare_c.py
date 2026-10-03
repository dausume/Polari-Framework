"""
@module board.custom.views.bare_c

THE BARE-C VIEW (brd-bo): cmod's `board_config.h` — the SAME text `pol board gen uno` writes for a variant (default uno-sim-rig),
its pin constants LED_PIN / PWM_PIN / ADC_CHANNEL taken from the BoardPin rows that carry those firmware symbols, under a banner
naming the board sha. gen.py itself writes the board_config.h WITHOUT the banner (its text stays byte-identical to dev-hn-0's, so
every .hex is unchanged); this view is the same knobs with provenance. Ingest reads the #defines back.
"""
import json
import re

from board.custom.views import ViewRefused, banner

FILE = 'board_config.h'


def render(r, bsha, variant='uno-sim-rig'):
    prof = r['profiles'].get('bare-c') or {}
    if not prof.get('supported'):
        raise ViewRefused('no bare-C view for %s: %s' % (r['board'], prof.get('refusal') or 'no bare-c RuntimeProfile row'))
    from board.custom import variants as V
    from board.custom.board_object import knobs_of
    knobs, src = knobs_of(r)
    res = V.resolve(V.find(variant), base=knobs)
    head = '/* %s\n * pins: %s */\n' % (banner('bare-c', r, bsha), ', '.join('%s = %s' % (k, src[k]) for k in sorted(src)))
    return {FILE: head + V.render_config(res)}


def parse(text):
    """{symbol: int} for every `#define NAME <int>` the bare-C side names a pin with."""
    from board.custom.board_object import SYMBOL_KNOBS
    out = {}
    for m in re.finditer(r'^\s*#define\s+([A-Z_][A-Z0-9_]*)\s+(-?\d+)', text, re.M):
        if m.group(1) in SYMBOL_KNOBS:
            out[m.group(1)] = int(m.group(2))
    return out


def ingest(files, r):
    """→ pins [{canonical, firmware_symbol}] — the canonical name rebuilt from the symbol's pin family in the rows (D / A)."""
    text = files.get(FILE) or next(iter(files.values()))
    out = []
    for sym, n in sorted(parse(text).items()):
        cur = next((p for p in r['pins'] if p.get('firmware_symbol') == sym), None)
        prefix = re.sub(r'\d+$', '', cur['canonical']) if cur else ('A' if sym == 'ADC_CHANNEL' else 'D')
        out.append({'canonical': '%s%d' % (prefix, n), 'firmware_symbol': sym})
    return {'pins': out, 'profile': {}, 'notes': json.dumps({'symbols': parse(text)})}

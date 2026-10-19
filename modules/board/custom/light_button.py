"""
@module board.custom.light_button

smp-1: THE CONFIG'S OWN BUTTON, for the per-config light proofs. The press check used to drive D2 (INT0) only, so a config whose button is on a pin-change pin (D4) or is read as a voltage on A0 was
refused ("button not on D2"). This module reads what the config itself says - its `button_route` and `button_pin` / `button_adc_channel` knobs, through the same rows the build is made from - and
says how the twin must press THAT button:

  int0   (no `button_route`)   --pin-at on PD2, falling then rising, 3 presses 150 ms apart
  pcint                        --pin-at on the SoC pin of `button_pin` (D4 -> PD4), the same presses
  adc                          the twin's triangle ramp on A0 (--adc0-ramp 200,4800,1000 for 3.6 s); the presses are the falling crossings of the press threshold, COUNTED BY A PURE MODEL of the ramp
                               with the config's own thresholds (board.custom.variant_twin.expected_presses) - the frames are compared with that count, never with a number typed here

Negative controls keep the same shape on every route (a real twin run each, judged by the same judge, which must reject it): NO press at all, and the same presses on a pin that is NOT the button
(pin routes) / a constant level that never crosses the threshold, and a switch already closed at boot (adc).
"""
from board.custom import variant_twin as VT

RAMP = VT.RAMP
RAMP_SECONDS = VT.RAMP_SECONDS
ADC_RELEASED_MV = 4800     # the button not pressed: A0 held at the pulled-up level
ADC_CLOSED_MV = 200        # the switch closed from boot


def plan(variant):
    """-> {route, pin (SoC pin name for the pin routes, '' for adc), wrong_pin, press_below_mv, release_above_mv, words} - read off the config's own knobs."""
    from board.custom import button_routes as BR
    from board.custom import variants as V
    k = V.resolve(V.find(variant))['knobs']
    route = str(k.get('button_route') or 'int0')
    out = {'route': route, 'pin': '', 'wrong_pin': '', 'press_below_mv': None, 'release_above_mv': None}
    if route == 'adc':
        out.update(press_below_mv=int(k['adc_press_below_mv']), release_above_mv=int(k['adc_release_above_mv']),
                   words='the button is a voltage on A%d (press below %d mV, release above %d mV), driven by the twin\'s ramp %d..%d mV over %d ms'
                         % (int(k.get('button_adc_channel', 0)), int(k['adc_press_below_mv']), int(k['adc_release_above_mv']), RAMP[0], RAMP[1], RAMP[2]))
        return out
    number = int(k['button_pin']) if route == 'pcint' else 2
    out['pin'] = BR._pin(number)[1]['pin']
    out['wrong_pin'] = 'PD2' if out['pin'] != 'PD2' else 'PD4'
    out['words'] = 'the button is on D%d (%s, %s)' % (number, out['pin'], 'external interrupt INT0' if route == 'int0' else 'pin-change interrupt')
    return out


def default_adc(variant):
    """The ADC0 flag the twin gets when no ramp is asked: the released level for a config that reads its button on A0 (a closed switch at boot is no press, but the released level is the honest rest),
    else None (the caller's own default stays: every other config's runs are unchanged)."""
    return '--adc0-mv %d' % ADC_RELEASED_MV if plan(variant)['route'] == 'adc' else None


def wire_args(variant):
    """The jumper of a config that carries the SENSE line: from the light pin (PD6) to the config's own sense pin (D3 polled, D8 on a pin-change interrupt) - the wire the bench needs - or [] for a config with none."""
    from board.custom import variant_twin as VT
    from board.custom import variants as V
    r = V.resolve(V.find(variant))
    return ['--wire', 'PD6:%s' % VT.sense_soc_pin(variant)] if r['features']['sense'] else []


def press_pinat(pl, n, start_cycle, hold, gap, pin=None):
    """--pin-at args for n presses on `pin` (default the button's own pin) -> (args, the cycle after the last press)."""
    pin = pin or pl['pin']
    out, c = [], start_cycle
    for _ in range(n):
        out += ['--pin-at', 'cycle=%d,pin=%s,level=0' % (c, pin), '--pin-at', 'cycle=%d,pin=%s,level=1' % (c + hold, pin)]
        c += gap
    return out, c


def ramp_presses(pl):
    """The press count a correct threshold reader must report for the ramp (the pure model, with the config's own thresholds)."""
    return VT.expected_presses(*RAMP, RAMP_SECONDS, pl['press_below_mv'], pl['release_above_mv'])

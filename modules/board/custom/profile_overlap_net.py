"""
@module board.custom.profile_overlap_net

pp-1: the SAME-NET rules - two pin profiles on two DIFFERENT pins wired together (the D6 -> D3 wire of the light bench). The rule that
decides most of it already exists in the code base and is cited, not re-written: board.custom.electrical_check rule (b)
`single_output` - a net with an output has EXACTLY one output; any number of inputs may listen. This module only sorts the kinds
onto the two sides of that rule (board.custom.profile_overlap_kinds.SIDE): driver | listener | bus (the TWI's open-drain wired-AND
lines) | by-mode (SPI: the master drives SCK/MOSI/SS and listens on MISO, the slave the reverse - Table 19-1) | reservation (the host link).
"""
from board.custom import profile_overlap_kinds as K
from board.custom.profile_overlap_pin import Outcome


def _o(verdict, mode, rule, reason, cites, cond=''):
    return Outcome(verdict, mode, 'net.' + rule, reason, cond, tuple(cites))


def rule(a, b):
    """Outcome for two kinds on ONE net (symmetric)."""
    if K.KINDS.index(a) > K.KINDS.index(b):
        a, b = b, a
    if not K.distinct_pairs(a, b):
        return _o('exclusive', 'exclusive', 'one-pin-only', 'the ATmega328P has only one pin that offers %s%s, so there are not two pins to wire together' % (a, '' if a == b else ' and %s' % b),
                  ('pin-tables', 'compat'))
    sa, sb = K.SIDE[a], K.SIDE[b]
    sides = {sa, sb}
    both = (sa, sb)
    # ---- the reservation: the USB-serial bridge drives the host link's net
    if 'reservation' in sides:
        other = sb if sa == 'reservation' else sa
        if other == 'listener':
            return _o('conditional', 'shared-read', 'transport-observed', 'another pin may listen to the host link\'s net (a listener adds no output), but it must never drive it and the transport pins themselves stay reserved',
                      ('single-output', 'lifecycle'), 'the other pin only listens to the net')
        return _o('exclusive', 'exclusive', 'transport-driven', 'the USB-serial bridge already drives the host link\'s net; a second output, bus or SPI line on it would fight it (a net has exactly one output)',
                  ('single-output', 'lifecycle'))
    # ---- listeners listen: any number of inputs
    if sa == sb == 'listener':
        return _o('compatible', 'shared-read', 'inputs-only', 'a net may have any number of inputs; the single-output rule only limits outputs (nothing here drives the net, so it floats unless something outside does)',
                  ('single-output', 'pinx-read'))
    if 'driver' in sides and 'listener' in sides:
        return _o('compatible', 'shared-read', 'one-output', 'exactly one output with inputs listening is the case the single-output rule marks ok - this is the D6 -> D3 jumper of the light bench',
                  ('single-output', 'pinx-read'))
    if sa == sb == 'driver':
        return _o('exclusive', 'exclusive', 'two-outputs', 'two outputs on one net fight (current flows between them); the single-output rule refuses it', ('single-output',))
    # ---- the TWI bus lines are open-drain on purpose
    if 'bus' in sides:
        other = sb if sa == 'bus' else sa
        if other == 'listener':
            return _o('compatible', 'shared-read', 'bus-listener', 'the bus line can be read by any input (a wired-AND line is a net with open-drain drivers and inputs)', ('twi-wired-and', 'single-output'))
        if other == 'bus':
            if a == b:
                return _o('compatible', 'shared-read', 'bus-wired-and', 'two pins on one bus line: every TWI driver is open-drain, so the line is wired-AND by design and several drivers are fine',
                          ('twi-wired-and',))
            return _o('exclusive', 'exclusive', 'two-bus-signals', 'SDA and SCL are two different signals; wiring them together makes one line carry both (the TWI needs two bus lines)', ('twi-wired-and',))
        if other == 'driver':
            return _o('exclusive', 'exclusive', 'push-pull-on-bus', 'a push-pull output on a TWI line breaks the wired-AND bus: all drivers must be open-drain, and a net has exactly one push-pull output',
                      ('twi-wired-and', 'single-output'))
        return _o('conditional', 'shared-read', 'bus-and-spi', 'an SPI pin can sit on a bus line only while it is an input (Table 19-1); as an output it is a push-pull driver on a wired-AND bus',
                  ('twi-wired-and', 'spi-pins', 'single-output'), 'the SPI pin is an input in the chosen master/slave mode')
    # ---- SPI pins: master/slave decides the direction
    if 'by-mode' in sides:
        other = sb if sa == 'by-mode' else sa
        if other == 'listener':
            return _o('compatible', 'shared-read', 'spi-and-listener', 'an SPI line is either an output (one driver, the listener hears it) or an input (nothing drives); in neither mode is there a second output',
                      ('spi-pins', 'single-output'))
        if other == 'driver':
            return _o('conditional', 'shared-read', 'spi-input-with-driver', 'the other pin is an output, so the SPI pin may only be an input there (two outputs fight; Table 19-1 gives the SPI directions)',
                      ('spi-pins', 'single-output'), 'the SPI pin is an input in the chosen master/slave mode (SCK, MOSI, SS inputs in slave mode; MISO an input in master mode)')
        if {a, b} == {'spi-mosi', 'spi-miso'}:
            return _o('conditional', 'shared-read', 'spi-loopback', 'MOSI wired to MISO is the classic SPI loopback test: as a master MOSI is the one output and MISO an input',
                      ('spi-pins', 'single-output'), 'the SPI is a master (MOSI drives, MISO listens)')
        return _o('conditional', 'shared-read', 'spi-pair', 'two SPI pins on one net work only while at most one of them is an output in the chosen mode (Table 19-1)',
                  ('spi-pins', 'single-output'), 'at most one of the two pins is an output in the chosen master/slave mode')
    return Outcome('undetermined', 'exclusive', 'net.unwritten', 'no rule is written for %s + %s on one net; not guessed' % (a, b), '', ('single-output',))

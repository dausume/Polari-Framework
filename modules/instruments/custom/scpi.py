"""
@module instruments.custom.scpi

osc-1 (OSCILLOSCOPE_PLAN.md §0, §3b): the two pieces of the IEEE 488.2 / SCPI standard a waveform needs, stdlib only, used by BOTH the
client (reading a real or emulated instrument) and the emulator (answering as one):

  IEEE 488.2 definite-length arbitrary block  (§7.7.6.2 of the standard; the `#9000001000...` every scope sends)
      block_encode(payload: bytes) -> bytes             '#' + one digit N + N digits of byte count + payload   (N = len(str(len(payload))))
      block_decode(data: bytes) -> (payload, consumed)  parses one block at the start of `data`; raises BlockError on a malformed header
      block_header_length(first_two: bytes) -> int      how many header bytes follow '#N' (so a socket reader knows how much to read next)
  SCPI command syntax (IEEE 488.2 §7 + SCPI-99 §6): a program message is `;`-separated units; a unit is a header (mnemonics joined by ':',
  a leading ':' = absolute, a trailing '?' = query) and space-separated / comma-separated arguments; mnemonics have a SHORT form (the capitals
  of the long form, e.g. WAVeform -> WAV) and both spell the same command, case-insensitive.
      parse_message(text) -> [Command(header_parts, query, args, raw)]
      short_form(mnemonic) -> 'WAV' for 'WAVeform'        long_or_short_match('WAV', 'WAVeform') -> True
      matches(parts, pattern) -> True when parts ('wav','data') match the pattern ('WAVeform','DATA') by long or short form
      idn(manufacturer, model, serial, firmware) -> the four-field *IDN? reply
Everything here is pure; nothing opens a socket.
"""
import re

MAX_HEADER_DIGITS = 9     # IEEE 488.2 allows 1..9 count digits ('#0' = indefinite length, which scopes do not use for waveform data)


class BlockError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------------- 488.2 blocks
def block_encode(payload):
    if not isinstance(payload, (bytes, bytearray)):
        raise BlockError('payload must be bytes')
    count = str(len(payload))
    if len(count) > MAX_HEADER_DIGITS:
        raise BlockError('payload too long for a definite-length block (%d bytes)' % len(payload))
    return b'#' + str(len(count)).encode() + count.encode() + bytes(payload)


def block_header_length(first_two):
    """Given the first two bytes ('#' + N), the number of COUNT digits that follow."""
    if len(first_two) < 2 or first_two[0:1] != b'#':
        raise BlockError('not a definite-length block header: %r' % first_two[:2])
    n = first_two[1:2]
    if not n.isdigit() or n == b'0':
        raise BlockError('block header digit must be 1-9, got %r' % n)
    return int(n)


def block_decode(data):
    """-> (payload, bytes_consumed). `data` must hold the whole block; a trailing newline after it is NOT consumed (the caller strips it)."""
    n = block_header_length(data[:2])
    digits = data[2:2 + n]
    if len(digits) < n or not digits.isdigit():
        raise BlockError('block count digits incomplete: %r' % digits)
    count = int(digits)
    start = 2 + n
    if len(data) < start + count:
        raise BlockError('block truncated: header says %d bytes, %d present' % (count, len(data) - start))
    return bytes(data[start:start + count]), start + count


# ---------------------------------------------------------------------------------------------------- SCPI syntax
class Command:
    __slots__ = ('parts', 'query', 'args', 'raw', 'absolute')

    def __init__(self, parts, query, args, raw, absolute):
        self.parts, self.query, self.args, self.raw, self.absolute = parts, query, args, raw, absolute

    def __repr__(self):
        return 'Command(%s%s%s)' % (':'.join(self.parts), '?' if self.query else '', (' ' + ', '.join(self.args)) if self.args else '')


_HEADER = re.compile(r'^\s*(\*?[A-Za-z][A-Za-z0-9_]*(?::[A-Za-z][A-Za-z0-9_]*)*)(\?)?\s*(.*)$')


def parse_message(text):
    """One program message -> its command units. A unit's header is split on ':' (a leading ':' marks it absolute; the common-command star
    '*IDN' is kept as one part). Arguments: the rest of the unit split on ',' (quotes are not needed by any scope command we send)."""
    out = []
    for unit in str(text).strip().split(';'):
        unit = unit.strip()
        if not unit:
            continue
        absolute = unit.startswith(':')
        m = _HEADER.match(unit[1:] if absolute else unit)
        if not m:
            raise ValueError('not a SCPI command unit: %r' % unit)
        header, q, rest = m.group(1), bool(m.group(2)), m.group(3).strip()
        args = [a.strip() for a in rest.split(',')] if rest else []
        out.append(Command(tuple(header.split(':')), q, args, unit, absolute))
    return out


def short_form(mnemonic):
    """SCPI-99 §6.2.1: the short form is the capitals of the long form (e.g. WAVeform -> WAV, SOURce -> SOUR, *IDN -> *IDN)."""
    caps = ''.join(c for c in mnemonic if c.isupper() or c == '*' or c.isdigit())
    return caps or mnemonic.upper()


def long_or_short_match(given, pattern):
    """`given` (any case) spells `pattern` (a long form with its capitals marking the short form) either fully or as the short form.
    A trailing channel digit is part of the mnemonic (CHANnel1 vs CHAN1) and is matched literally."""
    g = given.upper()
    return g == pattern.upper() or g == short_form(pattern).upper()


def matches(parts, pattern_parts):
    return len(parts) == len(pattern_parts) and all(long_or_short_match(p, q) for p, q in zip(parts, pattern_parts))


def idn(manufacturer, model, serial, firmware):
    """IEEE 488.2 §10.14: four comma-separated fields, no commas inside a field."""
    return ','.join(str(f).replace(',', ' ') for f in (manufacturer, model, serial, firmware))

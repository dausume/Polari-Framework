"""
@module board.custom.register_access

rm-2a (REGISTER_MAPPING_PLAN.md, his ask 2026-10-29: "make sure there are clear tables/object values that give details on what it means"): THE ACCESS
VOCABULARY of a RegisterField - one `RegisterAccessKind` row per word a field's `access` may hold, saying what a READ does, what a WRITE does, the
standard names the same behaviour has elsewhere, an example field, and the mistake it guards against. The words are Polari's short spellings; the
standard names are given beside them so a reader coming from a register tool recognises them:

  * IEEE 1800.2 (UVM) register field access policies (`uvm_reg_field`): RW, RO, W1C, W0C, W1T, ... - the verification world's names
  * CMSIS-SVD (the vendors' register-description XML): `access` (read-write | read-only | write-only) + `modifiedWriteValues` (oneToClear, zeroToClear,
    oneToToggle, ...) + `readAction`
Where neither standard has the exact behaviour, the row says so instead of borrowing a name. The standards are named, not re-read section by section here
(said in `basis`); every EXAMPLE is a field of this module's cited ATmega328P table.

  ACCESS_KINDS                 the rows (seeded as RegisterAccessKind)
  kind(word)                   -> the row, or None
  problems(field_rows)         -> fields whose access word has no row (the vocabulary must cover every field)
"""
_STD = 'IEEE 1800.2 UVM access policy names / CMSIS-SVD access + modifiedWriteValues names (named here, sections not re-read)'


def _k(name, title, read, write, uvm, svd, example, caution):
    return {'name': name, 'title': title, 'read_effect': read, 'write_effect': write, 'uvm_policy': uvm, 'svd_access': svd, 'example': example,
            'caution': caution, 'basis': _STD}


ACCESS_KINDS = [
    _k('rw', 'read / write', 'returns the value last written (or the reset value)', 'stores the value written',
       'RW', 'read-write', 'DDRD.DDD0 (pin PD0 direction)', 'none: an ordinary read-modify-write (x |= bit, x &= ~bit) is safe'),
    _k('r', 'read-only', 'returns the state the hardware sets', 'no effect (some fields ask that a write carry zero there: their row says so)',
       'RO', 'read-only', 'UCSR0A.RXC0 (receive complete)', 'software cannot set or clear it by writing; it changes when the hardware state changes'),
    _k('w1c', 'write one to clear', 'returns the flag: 1 = the event happened / a request is pending', 'writing 1 CLEARS the flag; writing 0 leaves it as it is',
       'W1C', 'read-write, modifiedWriteValues = oneToClear', 'EIFR.INTF0 (external interrupt 0 flag)',
       'a read-modify-write (EIFR |= bit) writes back a 1 to EVERY flag that is set and clears them all; write only the one bit (EIFR = bit)'),
    _k('w0c', 'write zero to clear', 'returns the flag: 1 = the event happened', 'writing 0 CLEARS the flag; writing 1 leaves it as it is (the datasheet names only '
       'the zero write)', 'W0C', 'read-write, modifiedWriteValues = zeroToClear', 'MCUSR.PORF (power-on reset flag)',
       'writing the whole register to 0 clears every flag at once (MCUSR = 0); to clear one flag and keep the others, write 1s to the others (MCUSR &= ~bit)'),
    _k('w-strobe', 'write to act (strobe)', 'always returns 0', 'writing 1 makes the hardware do something once (no state is kept)',
       '(no exact UVM policy: a write-only, self-clearing bit)', 'write-only (readAction none; reads as zero)', 'TCCR2B.FOC2A (force output compare A)',
       'reading it tells you nothing; writing it again repeats the action'),
    _k('rw-toggle', 'write one to toggle another bit', 'returns the pin\'s logic level', 'writing 1 TOGGLES the matching bit of ANOTHER register (PORTxn); 0 has no effect',
       '(no exact UVM policy: like W1T, but the toggled bit is in PORTx)', '(no exact SVD value: oneToToggle names a toggle of the bit itself)',
       'PIND.PIND3 (toggles PORTD3, §14.2.2)', 'a read-modify-write (PIND |= bit) toggles every PORTD bit whose pin reads high; write only the one bit'),
]
WORDS = tuple(k['name'] for k in ACCESS_KINDS)


def kind(word):
    return next((k for k in ACCESS_KINDS if k['name'] == word), None)


def problems(field_rows):
    """Fields whose access word the vocabulary lacks ([] = every field's word has a row)."""
    return ['%s.%s: access %r has no RegisterAccessKind row' % (f['register'], f['field'], f['access']) for f in field_rows if f['access'] not in WORDS]

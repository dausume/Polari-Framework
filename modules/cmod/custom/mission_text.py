"""
@module cmod.custom.mission_text

The PLAIN WORDS on a Hardware Mission drawing: for each of the six kinds of state, its card title (`displayName`) and the one
sentence beneath it (`purpose`). No plan names, no slice codes, no rulings - a person reading the card should learn what it says
without opening anything else. Pure strings over the Mission's own fields; `cmod.custom.mission_nocode` calls these.
"""
OBJECTIVE_WORDS = {'minimum-resources': 'the fewest resources', 'fastest-cycle': 'the fastest cycle'}
OBJECTIVE_SENTENCES = {
    'minimum-resources': ('Use as few resources as possible - pins, peripherals, program memory, data memory, processor time and parts on the '
                          'bench - while every required Purpose still stays inside its own limits (delay, debounce time, report rate).'),
    'fastest-cycle': ('Go through every Purpose as fast as possible with the resources the hardware on offer has; the resources are '
                      'a limit here, not something to save.')}
CYCLE_WORDS = ('A Purpose cycle is doing every task of one Purpose once; a Mission cycle is one pass through every Purpose. '
               'Cycle times come from the cycle counts measured on the digital twin, and are estimated from the size of the code '
               'until they are measured; each one says which it is.')
IMPORTANCE_WORDS = {'safety': 'Safety', 'required': 'Required', 'important': 'Important', 'desired': 'Desired'}
IMPORTANCE_SENTENCES = {
    'safety': 'Breaking this is never acceptable; it overrides everything else.',
    'required': 'The Mission fails without this.',
    'important': 'Counts heavily when solutions are compared.',
    'desired': 'Counts a little when solutions are compared.'}
PARTICIPANT_SENTENCES = {
    'hardware': 'A piece of hardware that takes part.', 'software': 'A piece of software that takes part.',
    'person': 'A person who takes part, such as the one pressing the button.'}
STAGE_WORDS = {'S1-breadboard': 'a breadboard', 'S2-protoboard': 'a protoboard', 'S3-pcb': 'a printed circuit board',
               'S4-vendor-soc': 'a vendor chip', 'S5-blcnc-soc': 'a custom chip'}
ESTIMATES = ('Not worked out yet: the time one pass through every Purpose takes, and the pins, memory and parts it uses, will appear '
             'here once candidate boards have been searched; each will say whether it was measured or estimated.')


def goal_card(m):
    title = m.get('title') or m.get('name', '')
    return title, '%s (life stage: %s)' % ((m.get('goal') or 'no goal written yet').rstrip('.') + '.', m.get('lifecycle') or 'enabled')


def settings_card(settings):
    obj = (settings or {}).get('objective') or 'minimum-resources'
    return ('Aims at: %s' % OBJECTIVE_WORDS.get(obj, obj),
            '%s %s' % (OBJECTIVE_SENTENCES.get(obj, 'Not a known aim.'), CYCLE_WORDS))


def purpose_card(row, derive=True):
    """row: one entry of mission_derived.purpose_rows."""
    imp = row.get('importance', '')
    title = '%s: %s' % (IMPORTANCE_WORDS.get(imp, imp or 'Purpose'), row.get('title') or row.get('purpose', ''))
    base = IMPORTANCE_SENTENCES.get(imp, 'How much this matters is not set.')
    if not row.get('known', True):
        return title, '%s There is no Purpose with this name, so nothing can be worked out for it.' % base
    if not derive:
        return title, '%s How far it is proven and whether it can run here are worked out when you ask; open its drawing to see them.' % base
    return title, ('%s Proof so far: %s. Can it run here: %s.' % (base, row.get('status', ''), (row.get('resolution', '') + ' - ' + row.get('why', ''))[:200]))


def participant_card(p):
    ref = p.get('ref') or '?'
    pending = (p.get('variant') or '') == 'pending'
    title = '%s: %s%s' % (p.get('role') or p.get('kind') or 'Participant', ref, ' (variant pending)' if pending else '')
    sentence = PARTICIPANT_SENTENCES.get(p.get('kind'), 'Something that takes part.')
    if pending:
        sentence += ' Its exact package and USB chip are still to be identified, and the Mission does not depend on them.'
    return title, sentence


def constraint_card(c):
    stage, boards = (c or {}).get('stage') or '', (c or {}).get('allowed_boards') or []
    parts = []
    if stage:
        parts.append('Stage of the hardware: %s' % STAGE_WORDS.get(stage, stage))
    if boards:
        parts.append('only these boards: %s' % ', '.join(boards))
    title = 'Limits: ' + ('; '.join(parts) if parts else 'none set')
    return title, 'What any solution must stay inside. A limit left empty is left open.'


def resolution_card(state, why, derive=True):
    if not derive:
        return 'Can it be done here?', 'Worked out from the Purposes the Mission needs when you ask; never stored.'
    return 'Can it be done here? %s' % state, why[:240]

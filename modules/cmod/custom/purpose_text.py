"""
@module cmod.custom.purpose_text

The PLAIN WORDS on a Purpose drawing: for each of the eleven states, its card title (`displayName`) and the one sentence beneath
it (`purpose`). No plan names, no slice codes, no rulings — a person reading the card should learn what it says without opening
anything else. Pure strings over the Purpose's own fields; `cmod.custom.purpose_nocode` calls these.
"""
KEY_WORDS = {'max_latency_ms': 'longest delay', 'debounce_ms': 'debounce time', 'freshness_ms': 'longest age of a value',
             'delivery': 'delivery', 'reliability': 'reliability', 'electrical_safety': 'electrical safety'}
KEY_SENTENCES = {
    'max_latency_ms': 'The most time that may pass between the cause and the result you can see.',
    'debounce_ms': 'How long a button must stay steady before a press counts, so contact bounce is not mistaken for several presses.',
    'freshness_ms': 'How old a value may be before it no longer counts as current.',
    'delivery': 'How a value reaches Polari: the latest value replaces the old one; events are kept and delivered in order.',
    'reliability': 'How sure it must be that nothing is lost on the way.',
    'electrical_safety': 'The electrical limit that must never be exceeded.'}
TRIGGER_SENTENCES = {
    'button': 'A press on a button on the board starts it.', 'command': 'A command sent from Polari starts it.',
    'period': 'The passing of a set period of time starts it.', 'boot': 'The board starting up starts it.'}
PARTICIPANT_SENTENCES = {
    'board': 'The board this runs on.', 'soc': 'The chip on the board that runs the program.',
    'host': 'The computer the board is plugged into, which carries the serial link.',
    'polari': 'Polari, which shows the state and sends the commands.'}
OBSERVES_SENTENCES = {
    'field': 'A state field Polari reads from the board.', 'event': 'Something that happens on the board and is reported as an event.',
    'correlation': 'The command number the board sends back, so an unrelated update is never mistaken for the command being done.'}


def goal_card(cap):
    title = cap.get('title') or cap.get('name', '')
    return title, '%s (life stage: %s)' % ((cap.get('goal') or 'no goal written yet').rstrip('.') + '.', cap.get('lifecycle') or 'enabled')


def depends_card(cap, dep_goal=''):
    dep = cap.get('depends_on') or ''
    if not dep:
        return 'Depends on: nothing', 'Nothing has to hold before this one; it comes first.'
    return 'Depends on: %s' % dep, 'This only counts once %s holds%s.' % (dep, (': ' + dep_goal.rstrip('.')) if dep_goal else '')


def participant_card(p):
    ref = p.get('ref') or '?'
    pending = (p.get('variant') or '') == 'pending'
    title = '%s: %s%s' % (p.get('role') or p.get('kind') or 'Participant', ref, ' (variant pending)' if pending else '')
    sentence = PARTICIPANT_SENTENCES.get(p.get('kind'), 'Something that takes part.')
    if pending and p.get('kind') == 'board':
        sentence += ' Its exact package and USB chip are still to be identified, and this Purpose does not depend on them.'
    return title, sentence


def trigger_card(t):
    what = (t or {}).get('what') or 'not stated yet'
    return 'When: %s' % what, TRIGGER_SENTENCES.get((t or {}).get('kind'), 'What starts it.')


def outcome_card(o):
    what = (o or {}).get('what') or 'not stated yet'
    return 'Then: %s' % what, 'The result you can observe when it has worked.'


def criterion_card(c):
    key = c.get('key', '')
    value = ('%s %s' % (c.get('value', ''), c.get('unit', ''))).strip()
    return 'Within: %s %s' % (KEY_WORDS.get(key, key.replace('_', ' ')), value), KEY_SENTENCES.get(key, 'A bound this Purpose must stay inside.')


def observes_card(o):
    delivery = o.get('delivery') or ''
    title = 'Polari must see: %s%s' % (o.get('item', ''), (' (%s)' % delivery) if delivery else '')
    return title, OBSERVES_SENTENCES.get(o.get('kind'), 'Something Polari must be able to observe.')


def tasks_card(names):
    if not names:
        return 'Done by: no tasks yet', 'No task is named for this Purpose yet.'
    return 'Done by: %d task%s' % (len(names), '' if len(names) == 1 else 's'), 'The tasks that do the work: %s.' % ', '.join(names)


def proof_card(scenario, status, last_proof, derived=True):
    if not scenario:
        return 'Proved by: no test yet', 'No test is named, so there is nothing to prove it with.'
    if not derived:
        return 'Proved by: %s' % scenario, 'How far it is proven is worked out from the runs of this test when you ask.'
    return ('Proved by: %s - %s' % (scenario, status),
            'How far it is proven, worked out from the runs of this test (never typed in)%s.' % ((': ' + last_proof) if last_proof else '; it has not been run yet'))


def resolution_card(state, why, derived=True):
    if not derived:
        return 'Can it run here?', 'Worked out from the real hardware bindings when you ask; never stored.'
    return 'Can it run here? %s' % state, why[:240]


def observed_card(summary, derived=True):
    if not derived:
        return 'On each device', 'Worked out from what each deployed board has reported when you ask; never stored.'
    return 'On each device', summary[:240]

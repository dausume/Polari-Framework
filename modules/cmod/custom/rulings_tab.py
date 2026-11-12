"""
@module cmod.custom.rulings_tab

msv-2 (AI-Notes/plans/MEASURED_VS_SIMULATED_PLAN.md sections 2 and 4): the RULINGS tab of /display/hardware-events - what waits for a person on the chosen
built unit, which build fault best explains its readings (a suggestion with its evidence), the ruling form, the rework form and every ruling with its
state. Configured tables and door-forms only (no new component).
"""
from polariApiServer.module_pages_seed import _component, _row, _table, _tab

_BS = '{scope:bench_solution}'
_REV = 'rev=r{scope:rev}'
_T = '/api/cmod/bench-topology/%s' % _BS
_U = _T + '/units/{scope:unit}'


def rulings_tab():
    rule = {'fields': [{'name': 'ruling', 'label': 'Ruling: accepted-variance | mistake | measurement-error', 'required': True},
                       {'name': 'cause', 'label': 'A mistake\'s cause: cold-joint | bridge | open | wrong-part-value | reversed-polarity | wrong-pin | damaged-part | other'},
                       {'name': 'scope', 'label': 'An accepted variance\'s scope: unit (default) | design | lot'},
                       {'name': 'who', 'label': 'Who rules', 'required': True},
                       {'name': 'words', 'label': 'Why, in your words (what you found)', 'type': 'textarea', 'required': True},
                       {'name': 'evidence_sha256', 'label': 'Evidence (a photo\'s sha256, optional)'}],
            'action': {'label': 'Rule', 'method': 'POST', 'path': _U + '/rulings',
                       'body_template': {'reading': '{scope:reading}', 'ruling': '{ruling}', 'cause': '{cause}', 'scope': '{scope}', 'who': '{who}', 'words': '{words}',
                                         'evidence_sha256': '{evidence_sha256}'}, 'then_scope': {'key': 'ruling', 'from': 'name'}},
            'submit_label': 'Rule on the chosen reading', 'success_text': 'Ruled - its state is in the table below.'}
    rework = {'fields': [{'name': 'words', 'label': 'What was done (e.g. reflowed the D6 joint, swapped R1 for a 220 ohm)', 'type': 'textarea', 'required': True},
                         {'name': 'who', 'label': 'Who did it', 'required': True}],
              'action': {'label': 'Keep', 'method': 'POST', 'path': _U + '/rulings/rework',
                         'body_template': {'ruling': '{scope:ruling}', 'words': '{words}', 'who': '{who}'}},
              'submit_label': 'Keep the rework on the chosen mistake', 'success_text': 'Kept. Now measure the point again: an in-band reading closes the mistake.'}
    return _tab('rulings', 'Rulings', [
        _row(0, [_table('he-queue', 0, 5, 'Waiting for a person - click one', '',
                        description='The unit\'s current readings the simulation does not explain (needs-ruling), the ones to measure again (re-measure), and the '
                                    'points with an open mistake. Pick the built unit on the Measured tab first; click a row to rule on it.',
                        columns='point,entered,verdict,standing,words', data_path=_U + '/ruling-queue?' + _REV, empty_text='Nothing waits for a person.',
                        select_field='reading', select_scope='reading', selected_value='{scope:reading}'),
                 _table('he-ranking', 5, 7, 'Which build fault explains the readings best (a suggestion)', '',
                        description='Every usual build fault (an open leg or joint, a bridge between nets, a wrong resistor value, a reversed LED, a wire on the '
                                    'neighbouring pin) is put into the circuit simulation, and scored against ALL of the unit\'s readings at once. explains = readings it '
                                    'predicts within their band; equal rank = the readings so far do not tell them apart. You still rule.',
                        columns='rank,fault,cause,explains,of,words', data_path=_U + '/fault-ranking?' + _REV, empty_text='No readings to rank yet.')], min_height=280),
        _row(1, [_table('he-ranking-words', 0, 12, 'What the ranking says, and what to measure next', '', columns='words',
                        data_path=_U + '/fault-ranking/summary?' + _REV, empty_text='')], min_height=120),
        _row(2, [_component('he-rule-form', 0, 6, 'Rule on the chosen reading', 'door-form', rule,
                            description='accepted-variance = the build is right and this is how it reads (this unit unless you say design or lot); mistake = the build '
                                        'is wrong (stays open until the point reads in band again); measurement-error = measure it again.'),
                 _component('he-rework-form', 6, 6, 'Rework on the chosen mistake', 'door-form', rework,
                            description='What was done to fix it. It does not close the mistake - the next in-band reading of the point does.')], min_height=260),
        _row(3, [_table('he-rulings', 0, 12, 'Rulings of the chosen unit - click one', '',
                        description='Every ruling, newest first. state: in-force, superseded (ruled again), open / closed (a mistake; closed_by = the in-band '
                                    're-read). suggested = the fault ranking\'s first suggestion when it was ruled, kept as evidence.',
                        columns='point,ruling,cause,scope,state,who,words,suggested,rework,closed_by,at', data_path=_U + '/rulings?' + _REV,
                        empty_text='No rulings yet.', select_field='name', select_scope='ruling', selected_value='{scope:ruling}')], min_height=240)],
        description='Readings the simulation does not explain, ruled by a person: accepted variance, a mistake with its cause, or a measurement error (msv-2).')

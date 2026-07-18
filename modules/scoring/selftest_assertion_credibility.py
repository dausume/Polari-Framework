"""
Selftest — assertion credibility voting (groups + individuals).

Run from polari-framework/:
    python3 -m scoring.selftest_assertion_credibility

Covers: personal votes and group stances count as DISTINCT units; a
member echoing their group's stance never double-counts the group; a
re-vote supersedes within its unit (rows retained — that is the
history); the reading is bounded below 1 by construction, rises with
each independent credible unit and falls with a not-credible one;
zero votes read as UNRATED (None) with the act suggested; small
samples flagged; the 'reading, not a truth declaration' framing is
pinned; and the scr-6 validity lifecycle is untouched by any of it
(a real transition runs alongside). Honest refusals throughout.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))

from scoring.assertion_credibility import (
    CREDIBILITY_LEVELS, assertion_credibility_reading,
    cast_credibility_vote)
from scoring.assertions import ScoreAssertion, transition_assertion

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _mgr():
    m = SimpleNamespace(idList=[], objectTables={
        'ScoreAssertion': {}, 'AssertionCredibilityVote': {},
        'Contributor': {}, 'ScoreGroup': {}}, db=None)
    for person in ('alice', 'bob', 'carol', 'dan', 'erin', 'frank'):
        m.objectTables['Contributor'][person] = SimpleNamespace(
            name=person)
    m.objectTables['ScoreGroup']['housing-guild'] = SimpleNamespace(
        name='housing-guild')
    m.objectTables['ScoreGroup']['tenant-union'] = SimpleNamespace(
        name='tenant-union')
    assertion = ScoreAssertion(
        name='assert-demo', subject_name='policy-x',
        intent='raises minimum wage', asserted_by='alice',
        manager=m)
    m.objectTables['ScoreAssertion']['assert-demo'] = assertion
    return m


def _units_and_supersession():
    print('distinct units + supersession')
    m = _mgr()
    first = cast_credibility_vote(
        m, 'assert-demo', 'alice', 'credible',
        rationale='matches the cited table', cast_at='2026-07-16T10:00:00')
    check('personal vote lands with its unit',
          first['ok'] and first['unit'] == 'individual:alice'
          and first['supersedes'] is None)
    stance = cast_credibility_vote(
        m, 'assert-demo', 'bob', 'credible',
        on_behalf_of_group='housing-guild',
        cast_at='2026-07-16T10:01:00')
    check('group stance is a second distinct unit',
          stance['ok'] and stance['unit'] == 'housing-guild')
    reading = assertion_credibility_reading(m, 'assert-demo')
    check('two units counted, both kinds listed',
          reading['distinctUnits'] == 2
          and reading['groupStances'] == ['housing-guild']
          and reading['individualVoters'] == ['alice'])
    two_unit_score = reading['score']

    echo = cast_credibility_vote(
        m, 'assert-demo', 'carol', 'questionable',
        on_behalf_of_group='housing-guild',
        cast_at='2026-07-16T10:02:00')
    reading = assertion_credibility_reading(m, 'assert-demo')
    check("a member re-casting the group's stance never "
          'double-counts the group',
          echo['ok'] and echo['supersedes'] == stance['vote']
          and reading['distinctUnits'] == 2
          and reading['supersededVotes'] == 1)
    check("the group's LATEST stance is the one read",
          reading['questionableCount'] == 1
          and reading['credibleCount'] == 1)

    revote = cast_credibility_vote(
        m, 'assert-demo', 'alice', 'not-credible',
        rationale='source retracted', cast_at='2026-07-16T10:03:00')
    reading = assertion_credibility_reading(m, 'assert-demo')
    check('a re-vote supersedes within its unit (rows retained)',
          revote['supersedes'] is not None
          and reading['voteCount'] == 4
          and reading['distinctUnits'] == 2
          and reading['notCredibleCount'] == 1)
    check('score is compared against the two-credible-unit reading '
          'and has fallen', reading['score'] < two_unit_score,
          f"{reading['score']} < {two_unit_score}")


def _score_properties():
    print('score properties (the sourcing_credibility formula)')
    m = _mgr()
    cast_credibility_vote(m, 'assert-demo', 'alice', 'credible',
                          cast_at='2026-07-16T11:00:00')
    one = assertion_credibility_reading(m, 'assert-demo')['score']
    check('one credible unit = 0.5 (1 / (1 + prior))', one == 0.5)
    cast_credibility_vote(m, 'assert-demo', 'bob', 'credible',
                          on_behalf_of_group='tenant-union',
                          cast_at='2026-07-16T11:01:00')
    two = assertion_credibility_reading(m, 'assert-demo')['score']
    check('a second independent credible unit STRICTLY raises it',
          two > one, f'{two} > {one}')
    cast_credibility_vote(m, 'assert-demo', 'dan', 'not-credible',
                          cast_at='2026-07-16T11:02:00')
    three = assertion_credibility_reading(m, 'assert-demo')['score']
    check('a not-credible unit STRICTLY lowers it', three < two,
          f'{three} < {two}')
    for i, person in enumerate(('erin', 'frank')):
        cast_credibility_vote(m, 'assert-demo', person, 'credible',
                              cast_at=f'2026-07-16T11:0{3 + i}:00')
    full = assertion_credibility_reading(m, 'assert-demo')
    check('bounded below 1 with five all-in units',
          full['score'] < 1.0, f"{full['score']}")
    check('five distinct units clears the small-sample flag',
          full['distinctUnits'] == 5
          and full['smallSample'] is False)


def _honesty():
    print('honesty (unrated, framing, lifecycle independence)')
    m = _mgr()
    empty = assertion_credibility_reading(m, 'assert-demo')
    check('zero votes = UNRATED (None), never zero, act suggested',
          empty['ok'] and empty['score'] is None
          and empty['suggestion']['knob'] == 'cast_credibility_vote')
    cast_credibility_vote(m, 'assert-demo', 'alice', 'credible',
                          cast_at='2026-07-16T12:00:00')
    reading = assertion_credibility_reading(m, 'assert-demo')
    check("the 'reading, not a truth declaration' framing is pinned",
          'not a truth declaration' in reading['reading'])
    check('small sample flagged under five units',
          reading['smallSample'] is True)

    moved = transition_assertion(m, 'assert-demo', 'under-review',
                                 by='moderator')
    after = assertion_credibility_reading(m, 'assert-demo')
    check('the scr-6 lifecycle moves independently and the reading '
          'only REPORTS it',
          moved['ok'] and after['validityStatus'] == 'under-review'
          and after['score'] == reading['score'])
    row = m.objectTables['ScoreAssertion']['assert-demo']
    check('casting votes never touched the assertion status',
          getattr(row, 'status', '') == 'under-review')


def _refusals():
    print('honest refusals')
    m = _mgr()
    check('unknown assertion lists known ones',
          cast_credibility_vote(m, 'assert-nope', 'alice',
                                'credible')['ok'] is False
          and 'assert-demo' in cast_credibility_vote(
              m, 'assert-nope', 'alice',
              'credible')['knownAssertions'])
    bad_level = cast_credibility_vote(m, 'assert-demo', 'alice',
                                      'certainly-true')
    check('unknown credibility level names the levels',
          not bad_level['ok']
          and bad_level['levels'] == list(CREDIBILITY_LEVELS))
    check('a voterless vote is refused (accountability)',
          not cast_credibility_vote(m, 'assert-demo', '',
                                    'credible')['ok'])
    ghost = cast_credibility_vote(m, 'assert-demo', 'nobody',
                                  'credible')
    check('unknown Contributor refused with the registration '
          'suggestion', not ghost['ok']
          and ghost['suggestion']['knob'] == 'Contributor')
    phantom = cast_credibility_vote(
        m, 'assert-demo', 'alice', 'credible',
        on_behalf_of_group='ghost-guild')
    check('unknown group refused with the group suggestion',
          not phantom['ok']
          and phantom['suggestion']['knob'] == 'ScoreGroup')
    cast_credibility_vote(m, 'assert-demo', 'alice', 'credible',
                          name='cred-x', cast_at='2026-07-16T13:00:00')
    dup = cast_credibility_vote(m, 'assert-demo', 'bob', 'credible',
                                name='cred-x')
    check('duplicate explicit vote name refused', not dup['ok'])
    check('unknown assertion reading lists known ones',
          'assert-demo' in assertion_credibility_reading(
              m, 'assert-nope')['knownAssertions'])


def main():
    _units_and_supersession()
    _score_properties()
    _honesty()
    _refusals()
    passed, total = sum(_results), len(_results)
    print(f'\n{passed}/{total} checks passed')
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())

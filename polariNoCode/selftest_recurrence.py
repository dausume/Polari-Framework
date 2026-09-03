"""
cal-1 recurrence selftest (check() style, no server): the `schedule`
field type finally expands — weekly/monthly/quarterly/semiannual/
yearly, bySetPos, once+duration, datetime spans, excludes, plain
refusals.

    python3 -m polariNoCode.selftest_recurrence
"""

import sys
from datetime import datetime

from polariNoCode.recurrence import describe_schedule, expand_schedule

_results = []


def check(label, cond, extra=''):
    _results.append((label, bool(cond)))
    print(f'{"PASS" if cond else "FAIL"}: {label}' + (f' — {extra}' if extra else ''))


def starts(occ):
    return [o['start'].strftime('%Y-%m-%d %H:%M') for o in occ]


def main():
    weekly = {'eventType': 'datetime', 'frequency': 'weekly', 'interval': 1,
              'byDay': ['SA'], 'startTime': '10:00', 'rangeStart': '2026-09-01'}
    occ = expand_schedule(weekly, '2026-09-01', '2026-09-30')
    check('weekly purchase (Saturdays 10:00) → 4 occurrences in September',
          starts(occ) == ['2026-09-05 10:00', '2026-09-12 10:00',
                          '2026-09-19 10:00', '2026-09-26 10:00'], str(starts(occ)))

    monthly = {'eventType': 'date', 'frequency': 'monthly', 'interval': 1,
               'byMonthDay': [1], 'rangeStart': '2026-09-01'}
    occ = expand_schedule(monthly, '2026-09-01', '2026-12-31')
    check('monthly bulk buy on the 1st → Sep, Oct, Nov, Dec (all-day)',
          starts(occ) == ['2026-09-01 00:00', '2026-10-01 00:00',
                          '2026-11-01 00:00', '2026-12-01 00:00']
          and all(o['allDay'] for o in occ), str(starts(occ)))

    for months, expect in ((3, ['2026-09-01 00:00', '2026-12-01 00:00',
                                '2027-03-01 00:00', '2027-06-01 00:00']),
                           (6, ['2026-09-01 00:00', '2027-03-01 00:00']),
                           (12, ['2026-09-01 00:00'])):
        sched = {'eventType': 'date', 'frequency': 'monthly',
                 'interval': months, 'byMonthDay': [1], 'rangeStart': '2026-09-01'}
        occ = expand_schedule(sched, '2026-09-01', '2027-08-31')
        check(f'every {months} months on the 1st over one year',
              starts(occ) == expect, str(starts(occ)))

    yearly = {'eventType': 'date', 'frequency': 'yearly', 'byMonth': [9],
              'byMonthDay': [1], 'rangeStart': '2026-09-01'}
    occ = expand_schedule(yearly, '2026-01-01', '2028-12-31')
    check('yearly bulk buy (Sep 1) → 2026, 2027, 2028',
          starts(occ) == ['2026-09-01 00:00', '2027-09-01 00:00', '2028-09-01 00:00'],
          str(starts(occ)))

    first_tue = {'eventType': 'date', 'frequency': 'monthly', 'byDay': ['TU'],
                 'bySetPos': [1], 'rangeStart': '2026-09-01'}
    occ = expand_schedule(first_tue, '2026-09-01', '2026-11-30')
    check('first Tuesday of the month (bySetPos) → Sep 1, Oct 6, Nov 3',
          starts(occ) == ['2026-09-01 00:00', '2026-10-06 00:00', '2026-11-03 00:00'],
          str(starts(occ)))

    last_fri = {'eventType': 'date', 'frequency': 'monthly', 'byDay': ['FR'],
                'bySetPos': [-1], 'rangeStart': '2026-09-01'}
    occ = expand_schedule(last_fri, '2026-09-01', '2026-10-31')
    check('last Friday of the month → Sep 25, Oct 30',
          starts(occ) == ['2026-09-25 00:00', '2026-10-30 00:00'], str(starts(occ)))

    once = {'eventType': 'date_duration', 'frequency': 'once',
            'rangeStart': '2026-09-10', 'durationDays': 3}
    occ = expand_schedule(once, '2026-09-11', '2026-09-30')
    check('once + 3-day duration overlapping the window start still counts',
          len(occ) == 1 and occ[0]['end'].strftime('%Y-%m-%d') == '2026-09-13',
          str(occ))

    workblock = {'eventType': 'datetime_duration', 'frequency': 'weekly',
                 'byDay': ['MO', 'TU', 'WE', 'TH', 'FR'], 'startTime': '09:00',
                 'endTime': '17:00', 'rangeStart': '2026-09-07', 'count': 5}
    occ = expand_schedule(workblock, '2026-09-01', '2026-09-30')
    check('weekday 09:00–17:00 with count=5 → five 8-hour spans, Mon–Fri',
          len(occ) == 5 and all((o['end'] - o['start']).total_seconds() == 8 * 3600 for o in occ)
          and starts(occ)[0] == '2026-09-07 09:00' and starts(occ)[-1] == '2026-09-11 09:00',
          str(starts(occ)))

    excl = dict(weekly, excludeDates=['2026-09-12'])
    occ = expand_schedule(excl, '2026-09-01', '2026-09-30')
    check('excludeDates removes exactly that Saturday',
          starts(occ) == ['2026-09-05 10:00', '2026-09-19 10:00', '2026-09-26 10:00'],
          str(starts(occ)))

    ended = dict(weekly, rangeEnd='2026-09-15')
    occ = expand_schedule(ended, '2026-09-01', '2026-09-30')
    check('rangeEnd stops the series', starts(occ) == ['2026-09-05 10:00', '2026-09-12 10:00'],
          str(starts(occ)))

    check('empty / {} schedule → no occurrences, no error',
          expand_schedule('', '2026-09-01', '2026-09-30') == []
          and expand_schedule('{}', '2026-09-01', '2026-09-30') == [])

    try:
        expand_schedule({'frequency': 'weekly'}, '2026-09-01', '2026-09-30')
        check('missing rangeStart refuses plainly', False)
    except ValueError as e:
        check('missing rangeStart refuses plainly', 'rangeStart' in str(e), str(e))
    try:
        expand_schedule({'frequency': 'fortnightly', 'rangeStart': '2026-09-01'},
                        '2026-09-01', '2026-09-30')
        check('unknown frequency refuses plainly', False)
    except ValueError as e:
        check('unknown frequency refuses plainly', 'fortnightly' in str(e), str(e))

    check('describe_schedule reads the rule back in words',
          describe_schedule(weekly) == 'every 1 week on SA at 10:00'
          and describe_schedule({'eventType': 'date', 'frequency': 'monthly',
                                 'interval': 3, 'byMonthDay': [1],
                                 'rangeStart': '2026-09-01'}) == 'every 3 months on day 1',
          describe_schedule(weekly))

    passed = sum(1 for _, ok in _results if ok)
    print(f'\n{passed}/{len(_results)} checks passed')
    return 0 if passed == len(_results) else 1


if __name__ == '__main__':
    sys.exit(main())

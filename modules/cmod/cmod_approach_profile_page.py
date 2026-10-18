"""
@module cmod.cmod_approach_profile_page

rt-0: /display/approach - which runtime a Hardware Mission needs, BEFORE any code is chosen, as CONFIGURED tables over the derived door (no raw JSON, no new
component): what the Mission demands, each tier checked against the Arduino UNO and the modelled ESP32-C3, and the derived priority order (a preview).
Reads GET /api/missions/<name>/approach?view=... (cmod.custom.approach_profile_doors).
"""
from polariApiServer.module_pages_seed import _page, _row, _table

_M = '/api/missions/uno-light-mission/approach'
_TIER_COLS = 'tier,verdict,why,flash,ram,kernel,variants,cost'
_TIER_WHAT = ('One row = one runtime tier. Columns: verdict (available, blocked with the board\'s own reason by name, or undetermined), why, flash and ram (the Mission\'s measured size '
              'against the board\'s cited limit; undetermined when the Mission has not been built for that chip), kernel (the tier\'s own footprint - measured or cited, otherwise undetermined, '
              'never guessed), variants (how many isotope variants of the six jobs stay eligible at that tier on that board), cost (what choosing the tier would cost you).')

APPROACH_PAGES = [
    _page('approach', 'approach',
          'Approach - which runtime a Hardware Mission needs: a bare C main loop with interrupts, FreeRTOS tasks, or Zephyr. It is worked out from what the Mission demands '
          '(its triggers and deadlines, the periodic tasks, the operations that wait, the data rate) and then checked against the hardware: memory, support by name, and which '
          'isotope variants stay possible. Every number says whether it is measured, estimated, cited, a criterion of the Purpose, or undetermined. This is advice, never a '
          'rule: a person can pick another tier and the cost is shown. From the command line: python3 -m cmod.custom.approach_profile mission uno-light-mission --board esp32-c3. '
          'The door: GET /api/missions/<name>/approach.',
          'HardwareMission', [
              _row(0, [_table('ap-demand', 0, 12, 'What the light Mission demands, and the tier that follows', 'HardwareMission',
                              description='What this is for: the demand summary and the recommendation with its reasons. One row = one thing the Mission demands or one step of the argument. '
                                          'Columns: item, value (with its label), detail. GET %s?view=demand.' % _M,
                              columns='item,value,detail', data_path='%s?view=demand' % _M)], min_height=380),
              _row(1, [_table('ap-tiers-uno', 0, 12, 'The three tiers on the Arduino UNO (ATmega328P)', 'HardwareMission', description=_TIER_WHAT, columns=_TIER_COLS,
                              data_path='%s?view=tiers&board=arduino-uno-r3' % _M)], min_height=260),
              _row(2, [_table('ap-tiers-c3', 0, 12, 'The same tiers on the modelled ESP32-C3', 'HardwareMission', description=_TIER_WHAT, columns=_TIER_COLS,
                              data_path='%s?view=tiers&board=esp32-c3' % _M)], min_height=260),
              _row(3, [_table('ap-priorities', 0, 12, 'Derived priorities - a preview (the real plan is the Task Plan page, /display/task-plan)', 'HardwareMission',
                              description='What this is for: the order the tasks would be served in. One row = one task of the loop. Rule: a shorter deadline is a higher priority; equal '
                                          'deadlines: the more important Purpose wins; still equal: the schedule order, marked as a tie. Nothing here is stored. GET %s?view=priorities.' % _M,
                              columns='priority,task,deadline,importance,serves,tie,note', data_path='%s?view=priorities' % _M)], min_height=260),
          ], title='Approach'),
]

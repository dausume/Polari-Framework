"""
@module cmod.cmod_solve_page

sol-0: /display/solutions-found - the answer of the attempt engine for the light Mission as CONFIGURED tables over the derived door (no raw JSON, no new component): the score card,
the chosen pin assignment with the reason for every pin, the trade study, "Designed for / Also runs on", and every branch that was pruned with its reason.
Reads GET /api/missions/<name>/solve?view=... (cmod.custom.solve_doors); the search itself is deterministic and cached by its inputs, so the five tables share one run.
"""
from polariApiServer.module_pages_seed import _page, _row, _table

_M = '/api/missions/uno-light-mission/solve'

SOLVE_PAGES = [
    _page('solutions-found', 'solutions-found',
          'Solutions found - the attempt engine tried every allowed Arduino UNO package and the modelled ESP32-C3, every runtime tier, and every way (isotope variant) of reading the button, '
          'driving the light and sensing its line, placed each choice on pins with the availability ladder, and scored the result by the Mission\'s aim. A plan that needs a part the bench '
          'does not have is listed and named, never called available. Every number says whether it is measured, estimated, cited or undetermined; an undetermined one is scored at a '
          'stated stand-in, never zero. From the command line: python3 -m cmod.custom.solve mission uno-light-mission. The door: POST /api/missions/<name>/solve.',
          'HardwareMission', [
              _row(0, [_table('sol-score-card', 0, 12, 'Score card - the ranking, and what decided it', 'HardwareMission',
                              description='What this is for: which plan wins and why the others lose. One row = one distinct plan (the same plan on another package is one row that says so). '
                                          'Columns: rank, verdict (chosen, runner-up, needs a part the bench lacks, could not be placed ...), candidate (hardware, tier and the way each job is done), '
                                          'score (the Mission\'s aim) and the other aim beside it, risks (open ladder rungs, parts, bounds), and the deciding difference from the chosen plan. GET %s?view=score-card.' % _M,
                              columns='rank,verdict,candidate,score,other_objective,risks,deciding_difference', data_path='%s?view=score-card' % _M)], min_height=420),
              _row(1, [_table('sol-assignment', 0, 12, 'The chosen plan - which pin for what, and why', 'HardwareMission',
                              description='What this is for: the pin plan of the chosen candidate. One row = one pin the plan needs. Columns: need, pin, function, importance, the Purposes that need it, '
                                          'why_this_pin (the least specialised pin that can do it, what else the pin carries that stays unused, the next best), refused_by_name (pins refused for this need and the '
                                          'ladder rung or claim that refused them - D0 and D1 are refused at rung 8), open_rungs (ladder rungs not checked). GET %s?view=assignment.' % _M,
                              columns='need,pin,function,importance,purposes,why_this_pin,refused_by_name,open_rungs', data_path='%s?view=assignment' % _M)], min_height=300),
              _row(2, [_table('sol-designed-for', 0, 12, 'Designed for, and also runs on', 'HardwareMission',
                              description='What this is for: where the chosen plan was made to work and where else the same choice of routes also works. One row = one hardware and tier. Columns: what '
                                          '(Designed for / Also runs on / Does not run on), hardware, tier, detail, how_we_know (resolver-valid means every checkable requirement is met but nothing has run on that hardware yet). '
                                          'GET %s?view=designed-for.' % _M,
                              columns='what,hardware,tier,detail,how_we_know', data_path='%s?view=designed-for' % _M)], min_height=220),
              _row(3, [_table('sol-trade-study', 0, 12, 'Trade study - every candidate side by side', 'HardwareMission',
                              description='What this is for: all candidates compared. One row = one candidate. Columns: hardware, tier, routes (the way each job is done), pins, resources (the weighted '
                                          'fraction of what the hardware has - lower is better), cycle (the estimated time to run once through every Purpose), parts_to_get, placement, open_rungs, '
                                          'undetermined_costs (how many costs were scored at a stand-in). GET %s?view=trade-study.' % _M,
                              columns='rank,hardware,tier,routes,pins,resources,cycle,cycle_basis,parts_to_get,placement,open_rungs,undetermined_costs', data_path='%s?view=trade-study' % _M)], min_height=420),
              _row(4, [_table('sol-pruned', 0, 12, 'Every branch that was pruned, and why', 'HardwareMission',
                              description='What this is for: nothing is dropped silently. One row = the first examples of one kind of pruned branch. Columns: kind (tier blocked, no variant, pin refused, '
                                          'could not be placed ...), count (how many of that kind), where, reason. GET %s?view=pruned.' % _M,
                              columns='kind,count,where,reason', data_path='%s?view=pruned' % _M)], min_height=300),
          ], title='Solutions found'),
]

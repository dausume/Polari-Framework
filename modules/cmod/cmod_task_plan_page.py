"""
@module cmod.cmod_task_plan_page

fgm-3: /display/task-plan - the Task Plan of the light Mission on its Hardware System as CONFIGURED tables over the derived door (no raw JSON, no new component): the tasks with their triggers, deadlines
and priorities (derived and edited side by side), the agreement check, the triggers in detail, the shared data an interrupt and the main loop both touch, the hand edits, and Designed for / Also runs on.
Reads GET /api/missions/<name>/task-plan?view=... (cmod.custom.task_plan_doors). With no stored solve run the page asks the attempt engine now (solve=now, cached) and says so.
"""
from polariApiServer.module_pages_seed import _page, _row, _table

_M = '/api/missions/uno-light-mission/task-plan'
_Q = 'solve=now'

TASK_PLAN_PAGES = [
    _page('task-plan', 'task-plan',
          'Task plan - the jobs the board does for the light Mission on the UNO light system, worked out by the computer from the Mission\'s Purposes, the atoms of the firmware graph and the attempt '
          'engine\'s chosen plan. Each task runs on ONE processor and is started by one trigger. Deadlines come from the Purposes\' own criteria; priority is deadline-monotonic (a shorter deadline '
          'is a higher priority, the more important Purpose wins a tie). A person can correct a priority, trigger, deadline, context or the order of the steps: the correction is kept beside the '
          'worked-out value with who, when and why, and survives a new derivation. The agreement check compares each task\'s context with the lane its atoms derive. '
          'From the command line: python3 -m cmod.custom.task_plan derive uno-light-mission --solve. The door: GET /api/missions/<name>/task-plan.',
          'HardwareMission', [
              _row(0, [_table('tp-tasks', 0, 12, 'The tasks, in priority order', 'HardwareMission',
                              description='What this is for: what the board does and how urgently. One row = one task. Columns: task, processor (each task is on exactly one), trigger (what starts it), '
                                          'deadline (from a Purpose criterion), priority (1 is the highest, 0 means no scheduler orders it; an edited value shows the worked-out one beside it), importance, '
                                          'context (init, isr, loop or task), steps (the atoms in order; the first may be the interrupt that feeds the task), agreement and the Purposes it serves. '
                                          'GET %s?view=tasks&%s.' % (_M, _Q),
                              columns='task,processor,trigger,deadline,priority,importance,context,steps,agreement,serves', data_path='%s?view=tasks&%s' % (_M, _Q))], min_height=330),
              _row(1, [_table('tp-agreement', 0, 12, 'Agreement check - does each task run where its atoms run?', 'HardwareMission',
                              description='What this is for: catching a task that is labelled one way while its code runs another. One row = one task. Columns: task, context (what the task is marked), '
                                          'lanes_of_its_atoms (the schedule lane each step derives: init, loop, called by another step, or isr), verdict (agrees, disagrees - named - or unchecked when no '
                                          'step of the chosen route exists in any graph yet) and why. GET %s?view=agreement&%s.' % (_M, _Q),
                              columns='task,context,lanes_of_its_atoms,verdict,why', data_path='%s?view=agreement&%s' % (_M, _Q))], min_height=300),
              _row(2, [_table('tp-triggers', 0, 12, 'Triggers - what starts each task', 'HardwareMission',
                              description='What this is for: how each task is started. One row = one trigger. Columns: kind (boot, edge, period, command, message), what, source (the pin or interrupt), '
                                          'how (interrupt or polled in the main loop - from the chosen route), route, debounce and period (from the Purposes\' criteria or the labelled estimate), notes. '
                                          'GET %s?view=triggers&%s.' % (_M, _Q),
                              columns='task,kind,what,source,how,route,debounce,period,notes', data_path='%s?view=triggers&%s' % (_M, _Q))], min_height=300),
              _row(3, [_table('tp-shared', 0, 12, 'Shared data - where an interrupt and the main loop touch the same thing', 'HardwareMission',
                              description='What this is for: the places the generated code will later need protection. One row = one piece of data a task touches. Columns: shared_data, kind (global, '
                                          'struct or struct field), access, touched_by (the steps), interrupt_and_loop (yes when an interrupt step and another step both touch it) and protected_today '
                                          '(whether the atom already wraps it in an atomic block). Nothing is changed. GET %s?view=shared-data&%s.' % (_M, _Q),
                              columns='task,shared_data,kind,access,touched_by,interrupt_and_loop,protected_today', data_path='%s?view=shared-data&%s' % (_M, _Q))], min_height=300),
              _row(4, [_table('tp-edits', 0, 12, 'Hand edits, beside the worked-out values', 'HardwareMission',
                              description='What this is for: a person\'s corrections of the worked-out plan. One row = one edit. Columns: task, field, derived_value (what the computer worked out), edited_value, who, '
                                          'when, why, and still_current (flagged when the worked-out value has changed since the edit was made). The edit is kept; nothing is overwritten. '
                                          'GET %s?view=edits&%s.' % (_M, _Q),
                              columns='task,field,derived_value,edited_value,who,when,why,still_current', data_path='%s?view=edits&%s' % (_M, _Q))], min_height=200),
              _row(5, [_table('tp-designed-for', 0, 12, 'Designed for, and also runs on', 'HardwareMission',
                              description='What this is for: where the plan was made to work and where else it is known to. One row = one hardware. Columns: what (Designed for is written once and never '
                                          'changed; Also runs on is added later), hardware, tier, detail (what had to change) and how_we_know (resolver-valid means every checkable requirement is met but nothing has '
                                          'run there; then proven-on-twin; then proven-on-hardware). GET %s?view=designed-for&%s.' % (_M, _Q),
                              columns='what,hardware,tier,detail,how_we_know', data_path='%s?view=designed-for&%s' % (_M, _Q))], min_height=220),
          ], title='Task plan'),
]

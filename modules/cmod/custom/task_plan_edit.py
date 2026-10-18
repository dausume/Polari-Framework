"""
@module cmod.custom.task_plan_edit

fgm-3: a person's correction of a DERIVED Task. It is a `DerivedOverride` (cmod.custom.overrides: who / when / why, one active row per field) on target class `TaskDefinition`, target name
'<plan>:<task>', shown BESIDE the derived value - the Task rows themselves hold only what the code derived, so a re-derive never loses an edit. Overridable fields:

  priority     a whole number (1 = highest; 0 = runs once at boot)
  trigger      boot | edge | period | command | message
  steps_order  the Task's step instance names, comma separated - must be exactly the same steps, reordered
  deadline_ms  a number of milliseconds
  context      init | isr | loop | task (the agreement check then compares the new context with the lanes of its atoms - and may say it disagrees)

When the derived value later CHANGES under an edit (the Mission, the criteria or the candidate moved), the edit is kept and FLAGGED with both values.
"""
OVERRIDABLE = ('priority', 'trigger', 'steps_order', 'deadline_ms', 'context')
TRIGGERS = ('boot', 'edge', 'period', 'command', 'message')
CONTEXTS = ('init', 'isr', 'loop', 'task')


def validate(task_row, field, value):
    """-> (cleaned string, '') or (None, why). `task_row` is the derived row (steps_order is checked against its steps)."""
    v = str(value).strip()
    try:
        if field == 'priority':
            if int(v) < 0:
                return None, 'priority is a whole number, 0 or more (1 is the highest)'
            return str(int(v)), ''
        if field == 'deadline_ms':
            if float(v) < 0:
                return None, 'deadline_ms is a number of milliseconds, 0 or more'
            return str(float(v)), ''
    except ValueError:
        return None, '%s needs a number (got %r)' % (field, value)
    if field == 'trigger':
        return (v, '') if v in TRIGGERS else (None, 'trigger is one of %s' % ', '.join(TRIGGERS))
    if field == 'context':
        return (v, '') if v in CONTEXTS else (None, 'context is one of %s' % ', '.join(CONTEXTS))
    if field == 'steps_order':
        names = [x.strip() for x in v.split(',') if x.strip()]
        have = [s['instance'] for s in task_row.get('steps', [])]
        if sorted(names) != sorted(have):
            return None, 'steps_order must be exactly this task\'s steps, reordered: %s' % ', '.join(have)
        return ','.join(names), ''
    return None, 'no overridable field %r (allowed: %s)' % (field, ', '.join(OVERRIDABLE))


def derived_row(target_name, manager):
    """The CURRENT derived row of '<mission>:<system>:<task>' (what overrides.create records as the derived value) - derived again from the run the stored plan was seeded from, edits NOT laid over it."""
    from cmod.custom import task_plan as TP
    from cmod.custom import task_plan_store as STORE
    plan_name, _s, task = target_name.rpartition(':')
    mission, _c, system = plan_name.partition(':')
    row = STORE.plan_row(plan_name, manager)
    try:
        plan = TP.derive_task_plan(mission, system, solve_run=(row.solve_run or None) if row is not None else None, manager=manager, apply_edits=False)
    except (ValueError, KeyError):
        return None
    return next((t for t in plan['tasks'] if t['name'] == target_name), None)


def edit(plan_name, task, field, value, why, who, manager):
    """Record a person's correction. -> (DerivedOverride row | None, why-not)."""
    from cmod.custom import overrides as OV
    name = '%s:%s' % (plan_name, task)
    row = derived_row(name, manager)
    if row is None:
        return None, 'no Task %r in Task Plan %r' % (task, plan_name)
    if field not in OVERRIDABLE:
        return None, 'TaskDefinition has no overridable field %r (allowed: %s)' % (field, ', '.join(OVERRIDABLE))
    clean, bad = validate(row, field, value)
    if clean is None:
        return None, bad
    return OV.create('TaskDefinition', name, field, clean, why, who, manager)


def apply_edits(plan, manager):
    """Lay every ACTIVE DerivedOverride of TaskDefinition over the plan's task rows, in place. Each edited row keeps the derived value beside it (`derived_<field>`), gets an `edits` list
    [{field, value, derived, who, when, why, flag}] and source 'edited'; the plan's source becomes 'edited' too. The agreement check is run again for an edited context / step order."""
    if manager is None:
        for t in plan['tasks']:
            t.setdefault('edits', [])
        return plan
    from cmod.custom import overrides as OV
    from cmod.custom import task_plan_steps as ST
    active = OV.active_overrides('TaskDefinition', manager)     # the same reader overrides.apply_overrides uses; the typed laying-over is done here (numbers, step order)
    for t in plan['tasks']:
        t['edits'] = []
        mine = active.get(t['name'], [])
        if not mine:
            continue
        t['derived_agreement'], t['derived_agreement_why'] = t['agreement'], t['agreement_why']
        for o in sorted(mine, key=lambda x: getattr(x, 'when', '')):
            fld = o.field
            if fld not in t:
                continue
            derived_now = t[fld]
            val = o.override_value
            flag = ''
            if str(derived_now) != o.derived_value:
                flag = 'CHANGED UNDER THIS EDIT: the derived value is now %s (it was %s when the edit was made) - the edit is kept; look at it again' % (derived_now, o.derived_value)
            applied = True
            try:
                if fld == 'priority':
                    t.setdefault('derived_priority', t['priority'])
                    t['priority'] = int(val)
                    t['priority_basis'] = 'edited by %s on %s: %s (derived: %s)' % (o.who or 'an unauthenticated request', o.when[:10], o.why, t['derived_priority'])
                elif fld == 'deadline_ms':
                    t.setdefault('derived_deadline_ms', t['deadline_ms'])
                    t['deadline_ms'] = float(val)
                    t['deadline_basis'] = 'edited by %s on %s: %s (derived: %s)' % (o.who or 'an unauthenticated request', o.when[:10], o.why, t['derived_deadline_ms'])
                elif fld == 'trigger':
                    t.setdefault('derived_trigger', t['trigger'])
                    t['trigger'] = val
                    t['agreement'], t['agreement_why'] = ST.agreement(t['context'], t['steps'], '', val)
                elif fld == 'context':
                    t.setdefault('derived_context', t['context'])
                    t['context'] = val
                    t['agreement'], t['agreement_why'] = ST.agreement(val, t['steps'], '', t['trigger'])
                elif fld == 'steps_order':
                    t.setdefault('derived_steps_order', t['steps_order'])
                    t.setdefault('derived_steps', list(t['steps']))
                    names = val.split(',')
                    by = {s['instance']: s for s in t['steps']}
                    if sorted(names) != sorted(by):
                        applied, flag = False, 'CANNOT APPLY: the steps are now %s and the edit names %s' % (', '.join(by), val)
                    else:
                        t['steps'] = [dict(by[n], n=i) for i, n in enumerate(names, 1)]
                        t['steps_order'] = val
            except ValueError:
                applied, flag = False, 'CANNOT APPLY: %r is not a valid %s' % (val, fld)
            t['edits'].append({'field': fld, 'value': val, 'derived': derived_now, 'who': o.who, 'when': o.when, 'why': o.why,
                               'flag': flag, 'ref': 'DerivedOverride:%s' % o.name, 'applied': applied})
        if t['edits']:
            t['source'] = 'edited'
    if any(t.get('edits') for t in plan['tasks']):
        plan['source'] = 'edited'
    return plan

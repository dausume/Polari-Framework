"""
@module firmwarefaults.custom.c3_trace

THE C3 TRACE, READ (sc-3): the UART1 lines the C3 template prints (board/custom/firmware/esp32c3/main/polari_trace.c) →
events, tasks, locks, the app's decision lines — and, rebuilt INDEPENDENTLY of the firmware's own verdict:

  wait_for(...)    the wait-for graph over time from the FreeRTOS hook events: TAKE makes a task a lock's holder, GIVE clears
                   it, BLOCK makes a task wait on a lock until it TAKEs it (or its timed take expires — TIMEOUT). After every
                   event the graph task → holder(lock it waits on) is checked for a cycle; the FIRST instant one closes is the
                   deadlock's time, the cycle its witness (T1 → B → T2 → A → T1). A cycle later broken by a TIMEOUT is
                   reported as transient.
  blocked(...)     every interval a task spent blocked on a lock (BLOCK → its TAKE), and WHO RAN during it (the switch-in
                   events, µs per task) — for priority inversion: how much of H's wait was M's run.

Event kinds are polari_trace.h's numbers. Times are the firmware's esp_timer µs (virtual time under -icount).
"""
import re

SWITCH_IN, TAKE, BLOCK, GIVE, INHERIT, DISINHERIT, MARK, TIMEOUT = 1, 2, 3, 4, 5, 6, 7, 8
KIND_NAMES = {1: 'SWITCH_IN', 2: 'TAKE', 3: 'BLOCK', 4: 'GIVE', 5: 'INHERIT', 6: 'DISINHERIT', 7: 'MARK', 8: 'TIMEOUT'}
MARKS = {1: 'REQ', 2: 'ACQ', 3: 'REL', 4: 'BUSY0', 5: 'BUSY1', 6: 'ROUND', 7: 'BACKOFF', 8: 'DONE'}
_KV = re.compile(r'(\w+)=(\S+)')


def kv(line):
    out = {}
    for k, v in _KV.findall(line):
        try:
            out[k] = int(v)
        except ValueError:
            out[k] = v
    return out


def parse(text):
    d = {'boot': {}, 'events': [], 'tasks': {}, 'locks': {}, 'rounds': [], 'pi': None, 'locks_line': None, 'deadlock': None,
         'trace': {}, 'end_us': 0, 'ended': False, 'steer': []}
    for raw in (text or '').splitlines():
        line = raw.strip()
        if line.startswith('@EV '):
            p = line.split()
            if len(p) == 6:
                d['events'].append(tuple(int(x) for x in p[1:]))
        elif line.startswith('@TASK '):
            p = line.split()
            d['tasks'][int(p[1])] = {'name': p[2], 'prio_at_dump': kv(line).get('prio')}
        elif line.startswith('@LOCK '):
            p = line.split()
            d['locks'][int(p[1])] = {'name': p[2], 'kind': p[3] if len(p) > 3 else ''}
        elif line.startswith('@ROUND '):
            p = [int(x) for x in line.split()[1:5]]
            d['rounds'].append({'round': p[0], 'req_us': p[1], 'acq_us': p[2], 'block_us': p[3]})
        elif line.startswith('@PI '):
            d['pi'] = kv(line)
        elif line.startswith('@LOCKS '):
            d['locks_line'] = kv(line)
        elif line.startswith('@DEADLOCK '):
            d['deadlock'] = kv(line)
        elif line.startswith('@TRACE '):
            d['trace'] = kv(line)
        elif line.startswith('@BOOT '):
            d['boot'] = kv(line)
        elif line.startswith('@STEER '):
            d['steer'].append(kv(line))
        elif line.startswith('@END'):
            d['ended'] = True
            d['end_us'] = int(kv(line).get('t_us', 0) or 0)
    return d


def name_of(d, task_id):
    return (d['tasks'].get(task_id) or {}).get('name', 'other' if task_id == 0 else 'task%d' % task_id)


def lock_name(d, lock_id):
    return (d['locks'].get(lock_id) or {}).get('name', 'lock%d' % lock_id)


def describe(d, ev):
    t, k, task, obj, arg = ev
    who = name_of(d, task)
    if k == SWITCH_IN:
        return '%s switched in' % who
    if k in (TAKE, BLOCK, GIVE, TIMEOUT):
        return '%s %s %s' % (who, {TAKE: 'takes', BLOCK: 'BLOCKS on', GIVE: 'gives', TIMEOUT: 'times out on'}[k], lock_name(d, obj))
    if k == INHERIT:
        return '%s raised to priority %d (inheritance)' % (who, arg)
    if k == DISINHERIT:
        return '%s back to priority %d' % (who, arg)
    if k == MARK:
        return '%s mark %s%s' % (who, MARKS.get(arg, arg), (' %s' % lock_name(d, obj)) if arg in (1, 2, 3) else (' %d' % obj))
    return '%s kind %d' % (who, k)


def _cycle(waits, holder):
    """A cycle in task → holder(waits[task]) — [task, lock, task, lock, …, task] or None."""
    for start in sorted(waits):
        path, seen, cur = [], {}, start
        while cur is not None and cur not in seen:
            seen[cur] = len(path)
            lock = waits.get(cur)
            if lock is None:   # a chain that ends in a task waiting for nothing: no cycle from this start
                cur = None
                break
            nxt = holder.get(lock)
            path += [('t', cur), ('l', lock)]
            cur = nxt
        if cur is not None and cur in seen:
            return path[seen[cur]:] + [('t', cur)]
    return None


def wait_for(d):
    """→ {first_cycle: {t_us, cycle: [names], event_index} | None, transient: [...], holders, waits (at the end), edges}."""
    holder, waits = {}, {}
    first, transient, open_cycle = None, [], None
    for i, ev in enumerate(d['events']):
        t, k, task, obj, arg = ev
        if k == TAKE:
            holder[obj] = task
            if waits.get(task) == obj:
                waits.pop(task, None)
        elif k == GIVE:
            if holder.get(obj) == task:
                holder.pop(obj, None)
        elif k == BLOCK:
            waits[task] = obj
        elif k == TIMEOUT:
            if waits.get(task) == obj:
                waits.pop(task, None)
        else:
            continue
        cyc = _cycle(waits, holder)
        if cyc and open_cycle is None:
            names = [name_of(d, x) if typ == 't' else lock_name(d, x) for typ, x in cyc]
            open_cycle = {'t_us': t, 'cycle': names, 'event_index': i}
            if first is None:
                first = dict(open_cycle)
        elif not cyc and open_cycle is not None:
            transient.append(dict(open_cycle, broken_at_us=t, broken_by=describe(d, ev)))
            open_cycle = None
    return {'first_cycle': first, 'persistent': open_cycle, 'transient': transient,
            'holders': {lock_name(d, l): name_of(d, t) for l, t in holder.items()},
            'waits': {name_of(d, t): lock_name(d, l) for t, l in waits.items()}}


def blocked(d, task_name, lock='R'):
    """Every interval `task_name` waited on `lock` (BLOCK → its TAKE) with who ran meanwhile (µs per task, from switch-ins)."""
    tid = next((i for i, x in d['tasks'].items() if x['name'] == task_name), None)
    lid = next((i for i, x in d['locks'].items() if x['name'] == lock), None)
    ev = d['events']
    out = []
    for i, (t, k, task, obj, arg) in enumerate(ev):
        if k != BLOCK or task != tid or obj != lid:
            continue
        end = next((j for j in range(i + 1, len(ev)) if ev[j][1] == TAKE and ev[j][2] == tid and ev[j][3] == lid), None)
        if end is None:
            out.append({'from_us': t, 'to_us': None, 'ran': {}, 'inherit': 0})
            continue
        ran, cur, since = {}, None, t
        for j in range(0, end + 1):
            tj, kj, taskj = ev[j][0], ev[j][1], ev[j][2]
            if kj != SWITCH_IN:
                continue
            if tj <= t:
                cur = taskj
                continue
            if cur is not None:
                ran[name_of(d, cur)] = ran.get(name_of(d, cur), 0) + (tj - since)
            cur, since = taskj, tj
        if cur is not None:
            ran[name_of(d, cur)] = ran.get(name_of(d, cur), 0) + (ev[end][0] - since)
        inh = sum(1 for j in range(i, end + 1) if ev[j][1] == INHERIT)
        out.append({'from_us': t, 'to_us': ev[end][0], 'wait_us': ev[end][0] - t, 'ran': ran, 'inherit': inh, 'event_index': i})
    return out


def round_times(d, task_name):
    """T1's round times: ROUND mark → its DONE mark (µs), per round that completed."""
    tid = next((i for i, x in d['tasks'].items() if x['name'] == task_name), None)
    out, start = [], None
    for t, k, task, obj, arg in d['events']:
        if k == MARK and task == tid and arg == 6:
            start = t
        elif k == MARK and task == tid and arg == 8 and start is not None:
            out.append(t - start)
            start = None
    return out

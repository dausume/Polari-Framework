"""
@module cmod.custom.confirmations

bss-3 (AI-Notes/plans/BENCH_SOLUTION_SIM_PLAN.md section 2 "Confirmation"): WHO SAYS A NODE WAS REACHED, and on which build. Written by the twin
(cmod.custom.node_run, when a run met the requirements with every edge check passing), by a person (attest), or from a hardware record (from_record:
a real board's observed field values and duration, judged against the SAME requirements). Never deleted: `void_for_build` marks every confirmation of
a node that holds for another hex sha256 as voided, saying which build it was for.

    confirm(manager, node, path, by, hex_sha256, run='', who='', words='')  -> the row (voids the node's confirmations of other builds first)
    attest(manager, node, who, words, path='')                              -> a person's confirmation (hex = the node's latest run's, or '')
    from_record(manager, node, path, record)                                -> a hardware confirmation, or ConfigRefused with the field that did not hold
                                                                               record = {hex_sha256, source, fields: {field: value}, duration_s}
    void_for_build(manager, node, hex_sha256, why='')                       -> the rows voided
    of(manager, node)                                                       -> the node's confirmations, newest first
"""
import datetime

from cmod.custom import config_rows as R


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def of(manager, node):
    return sorted(R.rows(manager, 'StructNodeConfirmation', node=node), key=lambda c: c['name'], reverse=True)


def void_for_build(manager, node, hex_sha256, why=''):
    out = []
    for c in R.rows(manager, 'StructNodeConfirmation', node=node, state='confirmed'):
        if c['hex_sha256'] and hex_sha256 and c['hex_sha256'] != hex_sha256:
            out.append(R.upsert(manager, 'StructNodeConfirmation', c['name'], state='voided',
                                voided_why=why or 'the build changed: it held for %s.., the current build is %s..' % (c['hex_sha256'][:12], hex_sha256[:12])))
    return out


def confirm(manager, node, path, by, hex_sha256, run='', who='', words=''):
    if R.get(manager, 'StructNode', node) is None:
        raise R.ConfigRefused('no node %r' % node, status=404)
    void_for_build(manager, node, hex_sha256)
    name = '%s#conf%d' % (node, len(R.rows(manager, 'StructNodeConfirmation', node=node)) + 1)
    return R.upsert(manager, 'StructNodeConfirmation', name, node=node, path=path, by=by, run=run, hex_sha256=hex_sha256, state='confirmed', who=who, words=words, at=_now())


def attest(manager, node, who, words, path=''):
    if not who or not words:
        raise R.ConfigRefused('a person\'s confirmation needs who and the words')
    runs = sorted(R.rows(manager, 'StructNodeRun', node=node), key=lambda r: r['name'])
    sha = runs[-1]['hex_sha256'] if runs else ''
    return confirm(manager, node, path, 'person', sha, who=who, words=words)


def from_record(manager, node, path, record):
    from cmod.custom.node_run import _holds
    fields = (record or {}).get('fields') or {}
    reqs = R.rows(manager, 'StructNodeRequirement', node=node)
    if not reqs:
        raise R.ConfigRefused('node %r has no requirements to judge the record against' % node)
    bad = [q for q in reqs if q['field'] not in fields or not _holds(q, fields[q['field']], q['field'] in fields)]
    if bad:
        raise R.ConfigRefused('the record does not meet %s' % '; '.join('%s %s %s (record: %s)' % (q['field'], q['kind'], q['value'], fields.get(q['field'], 'absent')) for q in bad))
    dur = record.get('duration_s')
    words = 'hardware record from %s: %s%s' % (record.get('source') or 'an unnamed source', ', '.join('%s = %s' % kv for kv in sorted(fields.items())),
                                                 ('; reached in %.3f ms' % (float(dur) * 1e3)) if dur is not None else '')
    return confirm(manager, node, path, 'hardware', str(record.get('hex_sha256') or ''), who=str(record.get('source') or ''), words=words)

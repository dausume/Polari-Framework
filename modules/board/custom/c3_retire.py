"""
@module board.custom.c3_retire

c3-derive: WHAT HAPPENS TO THE OLD STORED MATRIX ROWS. Before c3-derive a server's seed stored the ESP32-C3's 2 640 GPIO-matrix PinFunction rows; now they are DERIVED on read
(board.custom.soc_functions.pin_functions). A server whose DB still holds them is NOT wrong: the rows are identical to the derived ones and the accessor never repeats a stored name
(the stored copy answers), so every reader answers the same. They only cost boot time (restored on every start). Nothing in the seed deletes them (the seeder has no retirement pass and
data is never dropped silently); this is the explicit, opt-in step:

    retire_stored_matrix_rows(manager)              -> report, changes nothing (dry run)
    retire_stored_matrix_rows(manager, apply=True)  -> deletes ONLY stored rows that are field-for-field identical to the derived row of the same name; a row a person edited is
                                                       LEFT (listed in the report: the stored edit keeps winning over the derived one)
"""
from board.custom import soc_functions as SF


def _fields(row):
    from board.custom import board_object as BO
    return {k: v for k, v in BO.as_dict(row, 'PinFunction').items() if k != 'id'}


def retire_stored_matrix_rows(manager, apply=False):
    """-> {'stored': n matrix rows held, 'identical': n equal to the derived row, 'edited': [names], 'retired': n deleted (apply only), 'applied': bool}."""
    table = (getattr(manager, 'objectTables', None) or {}).get('PinFunction', {}) or {}
    derived = {f['name']: f for soc in SF.DERIVED for rows in SF.DERIVED[soc]().values() for f in rows}
    report = {'stored': 0, 'identical': 0, 'edited': [], 'retired': 0, 'applied': bool(apply)}
    keys = []
    for key, row in list(table.items()):
        want = derived.get(getattr(row, 'name', None))
        if want is None:
            continue
        report['stored'] += 1
        have = _fields(row)
        if all(str(have.get(k)) == str(v) for k, v in want.items() if k != 'provenance'):
            report['identical'] += 1
            keys.append((key, row.name))
        else:
            report['edited'].append(row.name)
    if apply:
        for key, name in keys:
            table.pop(key, None)
            try:
                manager.db.deleteRowsWhere('PinFunction', 'name', name)
            except Exception as e:   # the in-memory row is gone; the next boot would restore it - say so, never hide it
                report.setdefault('errors', []).append('%s: %s' % (name, e))
        report['retired'] = len(keys)
        print('[board] c3-derive: retired %d stored GPIO-matrix PinFunction rows (identical to the derived ones); %d edited rows left' % (len(keys), len(report['edited'])), flush=True)
    return report

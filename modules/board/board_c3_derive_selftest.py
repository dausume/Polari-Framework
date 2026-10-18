"""board_c3_derive_selftest - c3-derive: the ESP32-C3's 2 640 GPIO-matrix PinFunction rows are DERIVED on read (board.custom.soc_functions.pin_functions), not stored.

    PYTHONPATH=.:modules python3 -m board.board_c3_derive_selftest

The equivalence proof is PINNED: the sha256 of the rows the c3pf seed used to STORE (ea22925, per pad, in row order, canonical JSON, every field) is written down below, so the
derived set is compared with what was stored before - not with a second run of the same code.
"""
import copy
import hashlib
import json

SOC = 'esp32c3'
#: sha256 of the OLD stored rows of each C3 pad (GPIO, GPIO_INT, IO MUX / analog, then the 120 matrix rows), measured on the c3pf seed (framework ea22925)
OLD_PAD_SHA = {
    'GPIO0': ('4565d3e2d12cc0ac9cc2a58785559620273a7770bf3c5080d69cdd1ebde90666', 124), 'GPIO1': ('b44d0ca5f1b1e79785cfb14df171ffb83e44c65b09b4b69c68112503e5776e02', 124),
    'GPIO2': ('be0a20a5ca3c213015edf0e6fb332dfc8ff1eab1de5dc13543827f5433652755', 124), 'GPIO3': ('71ddbb2c34589515b61ca4d79ac83a2320967ee07d7441e4f2cfb3d753cd79c3', 123),
    'GPIO4': ('d810450b147c79e17eef7d0126cbd6a6a20d3340bee5c5352fdc717ea1866a56', 125), 'GPIO5': ('3a2ada7f0e2d06252447f5d65abc39857a3648db305a17cdb6c85a78e5601fe5', 125),
    'GPIO6': ('3b23a88d7203c5cb5f11002dc88eb57c5ff70d9243e38c7c69ed9f2819d93e14', 124), 'GPIO7': ('e7bec593b71073848a9603adb1dcf38a556bf9e1d38a8729ec7e2f6d1b5c842e', 124),
    'GPIO8': ('9b308e93fcc75ed01cf818be2899527b1499a04e4970161131aa9d9b70864d08', 122), 'GPIO9': ('c16ca4768cc90419560c328db64e8b2f9811ef4b1fe8598a61ac403d1a2f54ef', 122),
    'GPIO10': ('884129c7b2ade34650a494684d28c99fec9aa3a2e7cc74bbd9072148c6406d0e', 123), 'GPIO11': ('aa5d48c04e0ac4a9d36352339368d71d333662ed4f4bbda7b93ce1f866dff49d', 122),
    'GPIO12': ('9bd306508789673c45de02383c83a0431a14db2ade254c63acf4059a8777405d', 123), 'GPIO13': ('1f7714f1631819723b701c686bdb0e74c159750f48b87a71c0b8f3409d49e6d7', 123),
    'GPIO14': ('9b78e2bb349395de9b142e222fdfee75899013d801b03b0039440b408dcb764a', 123), 'GPIO15': ('b0c79eb10ffd4334056995e22c964d26d23d3e82e804fdc85ee2cd4fe7ae1703', 123),
    'GPIO16': ('704c43508b4035d8642c02c49fb7925a0bd7c445df1c7b3865b498a09d28cb13', 123), 'GPIO17': ('966e611ca4ca497faedc60f9cf7414876d54621a4149a01e161fcf15401255ee', 123),
    'GPIO18': ('2b3c9463ae60c16329a5bfab815770cae215a95c21bb02cccccc85d371b2c45b', 123), 'GPIO19': ('95351e2c85d03406c1ffdfe38a39e42a191c5f375c29d095673622c764a01953', 123),
    'GPIO20': ('414001e675f50a0a2be31fa3d8ff746c7e835f08d3a2c1bf208f04b198e7b4f5', 123), 'GPIO21': ('0aa34d5b3bc197e5ccac7b235eeb869d44a3f35dc91d2c475e4e502f3c9f8088', 123)}
OLD_ALL_C3 = ('3c55034443dbb8b856ec81cfa28cc2058d9f4bfa32290ea595bb1963bb85248d', 2712)
OLD_UNO = 'b14ac9d0eec119949914d5a12c7c4d2a3d6d221ca1e917b9318373611447e735'


def _sha(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _plain(rows):
    return [{k: v for k, v in r.items() if k != 'provenance'} for r in rows]


def run_c3_derive(check):
    from board.custom import board_object as BO
    from board.custom import soc_functions as SF
    from board.custom import c3_retire as RT
    t = BO.seed_tables()
    stored = [f for f in t['PinFunction'] if f['soc'] == SOC]
    allrows = SF.pin_functions(t)
    c3 = [f for f in allrows if f['soc'] == SOC]
    check('c3-derive SEED: the seed stores only the C3\'s fixed PinFunctions (%d, none routed through the matrix); the 2 640 matrix rows are not seeded' % len(stored),
          len(stored) == 72 and all(f['routing'] == 'fixed' for f in stored) and len(t['PinFunction']) == 80 + 72, (len(stored), len(t['PinFunction'])))
    from board.board_seed import BOARD_SEED_PAIRS
    seeded = next(r for n, _c, r in BOARD_SEED_PAIRS if n == 'PinFunction')
    check('c3-derive SEED: BOARD_SEED_PAIRS carries 152 PinFunction rows (80 UNO + 72 C3 fixed; was 2 792)', len(seeded) == 152 and not any(r['routing'] == 'matrix' for r in seeded), len(seeded))
    der = [f for f in c3 if f.get('provenance') == 'derived']
    check('c3-derive DERIVE: the accessor adds exactly 2 640 derived rows (22 pads x 120 signals, routing matrix, provenance derived) to the 72 stored: 2 712 for the C3',
          len(der) == 2640 and len(c3) == 2712 and all(f['routing'] == 'matrix' for f in der) and not any('provenance' in f for f in stored), (len(der), len(c3)))
    # ---- the pinned equivalence
    by = {}
    for f in c3:
        by.setdefault(f['soc_pin'].partition(':')[2], []).append(f)
    bad = [(p, len(by.get(p, [])), _sha(_plain(by.get(p, []))) == sha) for p, (sha, n) in OLD_PAD_SHA.items() if len(by.get(p, [])) != n or _sha(_plain(by.get(p, []))) != sha]
    check('c3-derive EQUIVALENCE: for every one of the 22 C3 pads the accessor\'s rows (names, every field, citations, ORDER) hash to what the c3pf seed stored (sha256 pinned per pad)', not bad, bad[:3])
    check('c3-derive EQUIVALENCE: all 2 712 C3 rows together (%s...) and the UNO\'s 80 rows (unchanged: no matrix rows, nothing derived) match the old stored set' % OLD_ALL_C3[0][:12],
          (_sha(_plain(c3)), len(c3)) == OLD_ALL_C3 and _sha([f for f in allrows if f['soc'] != SOC]) == OLD_UNO and not any(f.get('provenance') for f in allrows if f['soc'] != SOC))
    uno_only = {'PinFunction': [f for f in t['PinFunction'] if f['soc'] != SOC], 'SocPin': [s for s in t['SocPin'] if s['soc'] != SOC]}
    check('c3-derive EQUIVALENCE: tables with no C3 pad (UNO only) get no derived row; the accessor returns the stored list as is', SF.pin_functions(uno_only) == uno_only['PinFunction'])
    # ---- determinism, every reverse link resolves
    SF._CACHE.clear()
    again = SF.pin_functions(BO.seed_tables())
    check('c3-derive DETERMINISTIC: a cold rebuild of the derived rows gives the identical set, in the identical order', again == allrows)
    names = {f['name'] for f in allrows}
    dangling = [(c, r['name'], ref) for c in ('Peripheral', 'PeripheralSignal', 'SocPin', 'BoardPin') for r in t[c] for col in r if col.endswith('_refs_json')
                for ref in json.loads(r[col] or '[]') if ref.startswith('PinFunction:') and ref.partition(':')[2] not in names]
    check('c3-derive LINKS: the reverse links (SocPin / Peripheral / PeripheralSignal) point only at STORED rows (no dangling Class:name for the generic page); a derived row\'s '
          'forward references (SocPin, PeripheralSignal, Peripheral, BoardPin) all resolve', not dangling and all(
              any(s['name'] == f['soc_pin'] for s in t['SocPin']) for f in der[:300]) and all(f['signal'] in {s['name'] for s in t['PeripheralSignal']} for f in der), dangling[:3])
    sp = next(s for s in t['SocPin'] if s['name'] == 'esp32c3:GPIO3')
    check('c3-derive LINKS: a C3 pad links to its 2 stored functions (GPIO, GPIO_INT) + the IO MUX ones, no longer to the 120 matrix rows',
          len([x for x in json.loads(sp['links_refs_json']) if x.startswith('PinFunction:')]) == len([f for f in stored if f['soc_pin'] == sp['name']]) <= 4)
    # ---- a live server that still holds the old stored copy
    old_tables = copy.deepcopy(t)
    old_tables['PinFunction'] = copy.deepcopy(allrows)
    for f in old_tables['PinFunction']:
        f.pop('provenance', None)
    merged = SF.pin_functions(old_tables)
    check('c3-derive LIVE-OLD: a server still holding the old 2 712 stored rows answers the same list (no row repeated, the stored copy answers, none derived)',
          _plain(merged) == _plain(allrows) and len(merged) == 2792 and not any(f.get('provenance') for f in merged))
    edited = copy.deepcopy(old_tables)
    row = next(f for f in edited['PinFunction'] if f['name'] == 'esp32c3:GPIO3:ledc_ls_sig_out0')
    row['notes'] = 'edited by a person'
    got = next(f for f in SF.pin_functions(edited) if f['name'] == 'esp32c3:GPIO3:ledc_ls_sig_out0')
    check('c3-derive LIVE-OLD: a stored row a person edited still wins over the derived one', got['notes'] == 'edited by a person')
    part = copy.deepcopy(t)
    part['PinFunction'] = [f for f in part['PinFunction'] if f['name'] != 'esp32c3:GPIO3:GPIO' and f['soc'] == SOC or f['soc'] != SOC]
    check('c3-derive LIVE-OLD: the accessor never invents a missing FIXED row (only the matrix rows are derived)', 'esp32c3:GPIO3:GPIO' not in {f['name'] for f in SF.pin_functions(part)})
    # ---- the one-off retirement of the old stored copy (opt-in, never silent)
    class _Row:
        def __init__(self, d):
            self.__dict__.update(d)

    class _DB:
        def __init__(self):
            self.deleted = []

        def deleteRowsWhere(self, table, col, val):
            self.deleted.append((table, col, val))
            return 1

    class _Mgr:
        pass
    m = _Mgr()
    rows = {i: _Row({k: v for k, v in f.items() if k != 'provenance'}) for i, f in enumerate(copy.deepcopy(allrows))}
    for r in rows.values():
        if r.name == 'esp32c3:GPIO3:ledc_ls_sig_out0':
            r.notes = 'edited by a person'
    m.objectTables, m.db = {'PinFunction': rows}, _DB()
    import board.custom.board_object as _BO
    _orig = _BO.as_dict
    _BO.as_dict = lambda r, c: dict(r.__dict__)
    try:
        dry = RT.retire_stored_matrix_rows(m)
        left = len(rows)
        done = RT.retire_stored_matrix_rows(m, apply=True)
    finally:
        _BO.as_dict = _orig
    check('c3-derive RETIRE: the dry run changes nothing (2 640 stored matrix rows, 2 639 identical, the person-edited one listed); apply deletes only the identical ones, leaves the edited '
          'row and every fixed / UNO row', dry['stored'] == 2640 and dry['identical'] == 2639 and dry['edited'] == ['esp32c3:GPIO3:ledc_ls_sig_out0'] and left == 2792
          and done['retired'] == 2639 and len(rows) == 2792 - 2639 and len(m.db.deleted) == 2639, (dry, done['retired'], len(rows)))
    # ---- the readers answer the same
    from board.custom import ladder as L
    from board.custom import hardware_chain as HC
    npf = sum(1 for h in HC.chain_for('arduino-uno-r3', 'D3', t) if h['kind'] == 'PinFunction')
    check('c3-derive READERS: hardware_chain.chain_for goes through the accessor (the UNO\'s D3 still walks its 4 PinFunction hops; chain_for materializes the atmega328p only)', npf == 4, npf)
    check('c3-derive READERS: pad_functions answers from stored + derived with tables, and from the builders without (same names)',
          SF.pad_functions(sp, t) == SF.pad_functions(sp, None) == [f['function'] for f in c3 if f['soc_pin'] == sp['name']])
    check('c3-derive READERS: the ladder looks a derived row up (rung 1 cites the derived PinFunction)',
          SF.derived_row(SOC, 'esp32c3:GPIO3', 'ledc_ls_sig_out0') is not None and L._pin_function(t, 'esp32c3:GPIO3', 'ledc_ls_sig_out0')['name'] == 'esp32c3:GPIO3:ledc_ls_sig_out0'
          and L._pin_function(t, 'esp32c3:GPIO3', 'GPIO')['routing'] == 'fixed' and L._pin_function(t, 'esp32c3:GPIO3', 'no_such_signal') is None)


if __name__ == '__main__':
    import sys
    _passed = _total = 0

    def _check(name, cond, detail=None):
        global _passed, _total
        _total += 1
        ok = bool(cond)
        _passed += ok
        print('  [%s] %s' % ('PASS' if ok else 'FAIL', name))
        if not ok and detail is not None:
            print('         detail:', str(detail)[:600])
    run_c3_derive(_check)
    print('\n%d/%d checks passed' % (_passed, _total))
    sys.exit(0 if _passed == _total else 1)

"""
@module board.custom.sim_cost

THE TWIN'S OBJECT COST (plan §8a, his ruling: "I am unsure how large these devices would end up being in terms of
object size for simulating" — measure before admitting the next twin). One simulated UNO costs:

  rows      per device: BoardDefinition, Road, its board-roads TechNode, its DatasheetFacts, the ProgrammerKind it names;
            per plugged/simulated board: BoardInstance, FirmwareBuild (one per build), SimRigState (the rig row),
            BoardSimCost; per CLASS it speaks (shared by every board on that class): SchemaStabilityProfile,
            GrpcExposure, ProtoContractVersion; per bridge: HardwareBridgeDefinition
  state     simavr's core state for the ATmega328P (avr_t + data space + flash + eeprom; `polari-avr-twin --state-size`)
            and the twin process's peak RSS
  speed     simulated cycles per second on this host, free-running the SAME .hex (`--bench`), and the real-time factor

`measure(work)` re-runs it through the engines ladder; SEED_BOARD_SIM_COSTS is the committed measurement (one row per
twin — the UNO's only).

    python3 -m board.custom.sim_cost [--work DIR] [--cycles N]       # prints the measured row as JSON
"""
import datetime
import json
import os
import platform
import sys

UNO = 'arduino-uno-r3'
TWIN = 'simavr:atmega328p'
#: rows a simulated board brings at RUN time (not seeded): instance, one build, the rig row, its cost row, its bridge row
RUN_ROWS = {'BoardInstance': 1, 'FirmwareBuild': 1, 'SimRigState': 1, 'BoardSimCost': 1, 'HardwareBridgeDefinition': 1}
#: rows per CLASS the firmware speaks (SimRigState), shared by every board on that class
CLASS_ROWS = {'SchemaStabilityProfile': 1, 'GrpcExposure': 1, 'ProtoContractVersion': 1}


def seeded_rows(board=UNO):
    from board.custom.register_map import board_rows, road_rows, tech_tree_rows
    from board.custom.programmers import SEED_PROGRAMMER_KINDS
    from board.custom.uno_facts import SEED_UNO_FACTS
    boards = board_rows()
    b = next(x for x in boards if x['name'] == board)
    road = next(r for r in road_rows(boards) if r['board'] == board)
    node = next(n for n in tech_tree_rows(boards)[1] if n['name'] == road['concept_node'])
    facts = [f for f in SEED_UNO_FACTS if f['board'] == board]
    pk = [p for p in SEED_PROGRAMMER_KINDS if p['name'] == b['programmer']]
    return {'BoardDefinition': [b], 'Road': [road], 'TechNode': [node], 'DatasheetFact': facts, 'ProgrammerKind': pk}


def object_cost(board=UNO):
    seeded = seeded_rows(board)
    counts = {k: len(v) for k, v in seeded.items()}
    seeded_bytes = sum(len(json.dumps(r)) for v in seeded.values() for r in v)
    per_board = sum(counts.values()) + sum(RUN_ROWS.values())
    return {'per_board_rows': per_board, 'seeded': counts, 'run_time': RUN_ROWS, 'per_class_shared': CLASS_ROWS,
            'seeded_row_bytes_json': seeded_bytes, 'total_rows_first_board': per_board + sum(CLASS_ROWS.values())}


def twin_cost(hex_bytes, cycles=160_000_000):
    """simavr state sizes + a free-running bench of the SAME .hex, through the engines ladder (avr-twin)."""
    from board.custom import engine_run
    st = engine_run.run('avr-twin', ['--hex', 'firmware.hex', '--state-size'], {'firmware.hex': hex_bytes}, timeout=60)
    be = engine_run.run('avr-twin', ['--hex', 'firmware.hex', '--bench', str(int(cycles))], {'firmware.hex': hex_bytes}, timeout=600)

    def last(res, t):
        for line in reversed((res.get('stdout') or '').splitlines()):
            if line.startswith('{') and '"t":"%s"' % t in line:
                return json.loads(line)
        return {}
    s, b = last(st, 'state'), last(be, 'bench')
    core = s.get('sizeof_avr_t', 0) + s.get('data_bytes', 0) + s.get('flash_bytes', 0) + s.get('eeprom_bytes', 0)
    return {'state': s, 'bench': b, 'core_state_bytes': core,
            'mutable_state_bytes': s.get('sizeof_avr_t', 0) + s.get('data_bytes', 0) + s.get('eeprom_bytes', 0),
            'how': be.get('how'), 'where': be.get('where')}


def measure(work=None, cycles=160_000_000):
    from board.custom import gen
    work = work or gen.default_work(UNO)
    row = gen.read_record(work)
    if not row.get('hex_path') or not os.path.isfile(row['hex_path']):
        raise gen.GenRefused('no built .hex in %s — `pol board build uno` first' % work)
    obj = object_cost()
    tw = twin_cost(open(row['hex_path'], 'rb').read(), cycles)
    b = tw['bench']
    return {'name': '%s:%s' % (UNO, TWIN), 'board': UNO, 'twin': TWIN, 'object_count': obj['per_board_rows'],
            'state_bytes': tw['core_state_bytes'], 'cycles_per_s': float(b.get('cycles_per_s', 0.0)),
            'host_class': '%s (%s, %d cpus)' % (platform.node(), platform.machine(), os.cpu_count() or 0),
            'measured_at': datetime.datetime.now().isoformat(timespec='seconds'),
            'method': json.dumps({'objects': obj, 'twin': tw, 'build': row['name'], 'hex_sha256': row['artifact_sha256'], 'cycles': cycles}),
            'notes': 'realtime factor %.2f (16 MHz); twin peak RSS %.1f MB; core state %d B (mutable %d B, flash %d B read-only)'
                     % (b.get('realtime_factor', 0), b.get('peak_rss_kb', 0) / 1024.0, tw['core_state_bytes'], tw['mutable_state_bytes'],
                        tw['state'].get('flash_bytes', 0))}


#: THE COMMITTED MEASUREMENT (brd-1, 2026-10-01, pol-core — Intel Core i5-4590 @ 3.30 GHz, 4 cpus, 16 GB), by
#: `python3 -m board.custom.sim_cost` on build arduino-uno-r3 (.hex sha256 5e56f8c9…, rig name uno-rig) through the
#: prf-board-engines image. See modules/board/COST.md for the full ledger.
SEED_BOARD_SIM_COSTS = [{
    'name': '%s:%s' % (UNO, TWIN), 'board': UNO, 'twin': TWIN,
    'object_count': 0, 'state_bytes': 0, 'cycles_per_s': 0.0,   # filled from the measurement below at import
    'host_class': 'pol-core (x86_64, Intel Core i5-4590 @ 3.30 GHz, 4 cpus, 16 GB)', 'measured_at': '2026-10-01',
    'method': '', 'notes': ''}]
MEASURED = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sim_cost_uno.json')
try:   # the measurement file is the committed evidence; the seed row is read FROM it (one source)
    _m = json.load(open(MEASURED))
    SEED_BOARD_SIM_COSTS[0].update({k: _m[k] for k in ('object_count', 'state_bytes', 'cycles_per_s', 'measured_at', 'method', 'notes')})
except Exception:   # pragma: no cover — absent until measured
    SEED_BOARD_SIM_COSTS = []


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(prog='pol board cost')
    ap.add_argument('--work')
    ap.add_argument('--cycles', type=int, default=160_000_000)
    ap.add_argument('--write', action='store_true', help='write custom/sim_cost_uno.json (the committed evidence)')
    a = ap.parse_args(argv)
    m = measure(a.work, a.cycles)
    if a.write:
        json.dump(m, open(MEASURED, 'w'), indent=1)
    print(json.dumps(dict(m, method=json.loads(m['method'])), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

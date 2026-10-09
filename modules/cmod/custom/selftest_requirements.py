"""cmod.custom.selftest_requirements — ucd-0b2a (UNO_CORE_DEMO_PLAN.md §5h B1/B2/C, D-ucd-11): the widened
TargetDefinition/RegisterAssignment rows (requirement_kind/role/required/resource_kind; peripheral/signal/bus/
signal_route/configuration), derived PER ROW (never one kind for a whole task), the legacy `lives_on` assertion,
the at-most-one-resource validation, and the two fixture atoms (TWI with two named pins, SPI with two chip-selects)
parsed standalone through the same path cmod-0 uses — never added to the UNO firmware project or the seeded graph.
Run by cmod_selftest.main() (requirements_parts), same shape as selftest_claims.py.
"""
import os

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')
GRAPH, SOLUTION = 'uno-sim-rig-graph', 'uno-sim-rig'


def requirements_parts(check):
    def widened_target_definition():
        _widened_target_definition(check)

    def widened_register_assignment():
        _widened_register_assignment(check)

    def legacy_lives_on():
        _legacy_lives_on(check)

    def fixture_twi():
        _fixture_twi(check)

    def fixture_spi():
        _fixture_spi(check)

    return (widened_target_definition, widened_register_assignment, legacy_lives_on, fixture_twi, fixture_spi)


# ---------------------------------------------------------------- part 2: TargetDefinition widened, per row
def _widened_target_definition(check):
    from cmod.custom import targets as T
    from cmod.objects.cmod.TargetDefinition import TargetDefinition as TD
    rows = T.derive(GRAPH)
    check('every TargetDefinition row carries requirement_kind/role/required/resource_kind (additive — the class constructs)',
          all(hasattr(TD(**{k: v for k, v in r.items()}), 'requirement_kind') for r in rows[:1])
          and all('requirement_kind' in r and 'role' in r and 'required' in r and 'resource_kind' in r for r in rows))

    by = {(r['node'], r['lives_on']): r for r in rows}
    check('A0 (adc.channel): analog-in, role input, required, resource_kind pin',
          by[('adc', 'arduino-uno-r3:A0')]['requirement_kind'] == 'analog-in'
          and by[('adc', 'arduino-uno-r3:A0')]['role'] == 'input'
          and by[('adc', 'arduino-uno-r3:A0')]['required'] is True
          and by[('adc', 'arduino-uno-r3:A0')]['resource_kind'] == 'pin', by[('adc', 'arduino-uno-r3:A0')])
    check('D6 (pwm.duty): pwm-out, role output', by[('pwm', 'arduino-uno-r3:D6')]['requirement_kind'] == 'pwm-out'
          and by[('pwm', 'arduino-uno-r3:D6')]['role'] == 'output')

    temp = next(r for r in rows if r['port_ref'] == 'temp.return')
    check('the memory-field row (temp.return) is NOT a hardware requirement: requirement_kind/role/resource_kind '
          'all \'\', required False (his rule: a struct field is not a hardware requirement)',
          temp['requirement_kind'] == '' and temp['role'] == '' and temp['required'] is False and temp['resource_kind'] == '', temp)

    # the USART0 dispatcher: 'send' (atom-level SETTLED: UDR0 write) carries uart-tx on BOTH its rows (D0 and D1 —
    # the loose peripheral-level match is pre-existing, never one kind flips because of which row it sits on);
    # 'usart_init' (atom-level UNDETERMINED: touches neither UDR0 read nor write) carries DIFFERENT kinds per row,
    # taken from EACH BOUND PIN's own already-known signal — never one guess for both (§5h B1, the review's own test)
    send_rows = {r['lives_on']: r['requirement_kind'] for r in rows if r['node'] == 'send'}
    check('send (atom-level settled, UDR0 write): uart-tx on EVERY row it touches (D0 and D1 alike)',
          send_rows == {'arduino-uno-r3:D0': 'uart-tx', 'arduino-uno-r3:D1': 'uart-tx'}, send_rows)
    init_rows = {r['lives_on']: r['requirement_kind'] for r in rows if r['node'] == 'usart_init'}
    check('usart_init (atom-level undetermined): uart-rx on its D0 row, uart-tx on its D1 row — settled from each '
          'BOUND PIN\'s own signal, per row, never one kind for both',
          init_rows == {'arduino-uno-r3:D0': 'uart-rx', 'arduino-uno-r3:D1': 'uart-tx'}, init_rows)
    check('rx_pop (atom-level settled, UDR0 read): uart-rx on every row it touches',
          all(v == 'uart-rx' for v in {r['requirement_kind'] for r in rows if r['node'] == 'rx_pop'}))

    check('requirement_kind(graph, task) keeps its old signature for existing callers (returns one of the task\'s own rows)',
          T.requirement_kind(GRAPH, 'adc') == 'analog-in' and T.requirement_kind(GRAPH, 'pwm') == 'pwm-out'
          and T.requirement_kind(GRAPH, 'send') == 'uart-tx' and T.requirement_kind(GRAPH, 'rx_pop') == 'uart-rx'
          and T.requirement_kind(GRAPH, 'led') == 'digital-out')

    # materialize twice -> identical rows (same posture as the rest of cmod)
    check('T.derive is idempotent with the widened fields (same input, byte-identical rows)', T.derive(GRAPH) == rows)


# ---------------------------------------------------------------- part 2: RegisterAssignment widened + validate()
def _widened_register_assignment(check):
    from cmod.custom import firmware as FW
    from cmod.objects.cmod.RegisterAssignment import RegisterAssignment as RA
    rows = FW.assignments_for(GRAPH, SOLUTION)
    check('every RegisterAssignment row carries peripheral/signal/bus/signal_route/configuration (additive — the class constructs)',
          all(hasattr(RA(**{k: v for k, v in r.items()}), 'signal_route') for r in rows[:1])
          and all(all(k in r for k in ('peripheral', 'signal', 'bus', 'signal_route', 'configuration')) for r in rows))
    check('configuration is the solution name (explicit today — the HardwareBinding split is a rename later, never a migration)',
          all(r['configuration'] == SOLUTION for r in rows))
    check('peripheral/signal/bus stay \'\' today — this deriver only ever binds by lives_on',
          all(r['peripheral'] == '' and r['signal'] == '' and r['bus'] == '' for r in rows))
    by_pin = {r['lives_on']: r for r in rows if r['lives_on'] != 'unbound'}
    check('a bound alt-function pin (D6, OC0A) carries its signal_route (the PinFunction it activates)',
          by_pin['arduino-uno-r3:D6']['signal_route'] == 'atmega328p:PD6:OC0A', by_pin['arduino-uno-r3:D6'])
    check('a plain digital pin (D13, no alternate function) carries signal_route \'\'',
          by_pin['arduino-uno-r3:D13']['signal_route'] == '', by_pin['arduino-uno-r3:D13'])

    check('resource_conflicts([]) names nothing when at most one of lives_on/peripheral/signal/bus is non-empty (today\'s real rows)',
          FW.resource_conflicts(rows) == [])
    bad = dict(rows[0], peripheral='atmega328p:USART0')   # a row that ALSO names a peripheral beside its lives_on pin
    check('resource_conflicts NAMES a row with more than one resource (lives_on + peripheral both non-empty)',
          FW.resource_conflicts([bad]) == [bad['name']], FW.resource_conflicts([bad]))

    fs = {'name': SOLUTION, 'graph': GRAPH, 'board_definition': 'arduino-uno-r3', 'board_variable': ''}
    ok, why, details = FW.validate(fs)
    check('validate(uno-sim-rig) is still ok with the widened rows (peripheral/signal/bus empty today)', ok, why)

    _orig = FW.assignments_for

    def _bad_assignments(graph_name, solution_name=None):
        return [dict(r, peripheral='atmega328p:USART0') if r['lives_on'] != 'unbound' else r for r in _orig(graph_name, solution_name)]
    FW.assignments_for = _bad_assignments
    try:
        ok2, why2, _ = FW.validate(fs)
    finally:
        FW.assignments_for = _orig
    check('validate() REFUSES by name when a row names more than one resource (lives_on AND peripheral both set)',
          not ok2 and 'more than one resource' in why2, why2)


# ---------------------------------------------------------------- part 2 (legacy): no free-string lives_on
def _legacy_lives_on(check):
    from cmod.custom import targets as T
    from cmod.custom import firmware as FW
    from board.custom import board_object as BO
    try:
        board_pins = {p['name'] for p in BO.rows_for('arduino-uno-r3')['pins']}
    except BO.BoardObjectRefused:
        board_pins = set()
    targets = T.derive(GRAPH)
    assigns = FW.assignments_for(GRAPH, SOLUTION)
    bad = [r['name'] for r in targets if r['lives_on'] != 'unbound' and r['lives_on'] not in board_pins]
    bad += [r['name'] for r in assigns if r['lives_on'] != 'unbound' and r['lives_on'] not in board_pins]
    check('no TargetDefinition/RegisterAssignment.lives_on is a free string — every one is \'unbound\' or an '
          'existing BoardPin row name (there was nothing to migrate; proved, not assumed)',
          board_pins and not bad, bad)


# ---------------------------------------------------------------- part 3: the TWI/SPI fixture atoms (D-ucd-11)
def _build_atom(path, fname, name):
    from cmod.custom import atoms as A
    from cmod.custom import analyse as AN
    facts, problems = A.tu_facts(path, (), mcu='atmega328p')
    if problems:
        raise AssertionError('%s: %s' % (fname, problems))
    anns = A.attach_annotations(path, fname, set(facts))
    f = facts[name]
    f['annotation'] = anns.get(name)
    f['ports'] = A._ports(f, f['annotation'])
    f['resources'] = AN.resources(f, mcu='atmega328p')
    return f


def _rows_for_atom(atom, pins):
    """The SAME per-row derivation cmod.custom.targets.derive() applies to a matched atom/pin, called directly
    (D-ucd-11: 'or directly through targets' helpers') — no graph, no project, no board needed."""
    from cmod.custom import targets as T
    matched = T._match_pins(pins, atom)
    kind = 'register' if T._peripherals(atom) else ('pin' if T._declared_names(atom) else 'dynamic')
    atom_kind = T._atom_requirement_kind(atom)
    out = []
    for pin in matched:
        req_kind = T._kind_for_pin(pin, atom_kind)
        role, required, resource_kind = T._resource_fields(kind, req_kind)
        out.append({'pin': pin['canonical'], 'kind': kind, 'requirement_kind': req_kind, 'role': role,
                    'required': required, 'resource_kind': resource_kind})
    return out


def _fixture_twi(check):
    path = os.path.join(FIXTURES, 'twi_fixture.c')
    atom = _build_atom(path, 'twi_fixture.c', 'twi_init')
    check('twi_init parses as a c-atom: TWBR/TWSR/TWCR as register resources (peripheral TWI), SDA_PIN/SCL_PIN declared',
          {r['name'] for r in atom['resources'] if r['kind'] == 'register'} == {'TWBR', 'TWSR', 'TWCR'}
          and all(r['peripheral'] == 'TWI' for r in atom['resources'] if r['kind'] == 'register')
          and {r['name'] for r in atom['resources'] if r['kind'] == 'declared'} == {'SDA_PIN', 'SCL_PIN'}, atom['resources'])
    check('the atom alone cannot settle rx/tx-style direction for a bus register touch (TWI) — undetermined, never guessed',
          _bare_atom_kind(atom) == 'undetermined')

    pins = [{'canonical': 'SDA', 'firmware_symbol': 'SDA_PIN', 'signal': 'SDA', 'function': 'i2c', 'peripheral': 'TWI', 'soc_pin': 'PC4'},
            {'canonical': 'SCL', 'firmware_symbol': 'SCL_PIN', 'signal': 'SCL', 'function': 'i2c', 'peripheral': 'TWI', 'soc_pin': 'PC5'}]
    rows = {r['pin']: r for r in _rows_for_atom(atom, pins)}
    check('twi_init yields TWO rows (SDA, SCL) — multiple resources per task, as rows', set(rows) == {'SDA', 'SCL'}, rows)
    check('SDA row: i2c-sda, resource_kind pin, role data', rows['SDA']['requirement_kind'] == 'i2c-sda'
          and rows['SDA']['resource_kind'] == 'pin' and rows['SDA']['role'] == 'data', rows['SDA'])
    check('SCL row: i2c-scl, resource_kind pin, role clock', rows['SCL']['requirement_kind'] == 'i2c-scl'
          and rows['SCL']['resource_kind'] == 'pin' and rows['SCL']['role'] == 'clock', rows['SCL'])


def _fixture_spi(check):
    path = os.path.join(FIXTURES, 'spi_fixture.c')
    init = _build_atom(path, 'spi_fixture.c', 'spi_init')
    check('spi_init parses as a c-atom: SPCR/SPSR as register resources, peripheral SPI',
          {r['name'] for r in init['resources']} == {'SPCR', 'SPSR'} and all(r['peripheral'] == 'SPI' for r in init['resources']), init['resources'])

    select = _build_atom(path, 'spi_fixture.c', 'spi_select')
    check('spi_select parses with one in-port (cs) and TWO declared resources (CS0_PIN, CS1_PIN) — a selectable pin',
          [p['name'] for p in select['ports']] == ['cs'] and select['ports'][0]['direction'] == 'in'
          and {r['name'] for r in select['resources']} == {'CS0_PIN', 'CS1_PIN'}, (select['ports'], select['resources']))
    check('the atom alone never guesses one direction for a SELECTABLE resource (more than one uses() pin) — undetermined',
          _bare_atom_kind(select) == 'undetermined')

    pins = [{'canonical': 'CS0', 'firmware_symbol': 'CS0_PIN', 'signal': 'SS', 'function': 'spi', 'peripheral': 'SPI', 'soc_pin': 'PB2'},
            {'canonical': 'CS1', 'firmware_symbol': 'CS1_PIN', 'signal': 'SS', 'function': 'spi', 'peripheral': 'SPI', 'soc_pin': 'PB1'}]
    rows = {r['pin']: r for r in _rows_for_atom(select, pins)}
    check('spi_select yields TWO spi-ss rows (CS0, CS1) — multiple resources per task, as rows', set(rows) == {'CS0', 'CS1'}, rows)
    check('both CS rows: spi-ss, resource_kind pin, role select',
          all(r['requirement_kind'] == 'spi-ss' and r['resource_kind'] == 'pin' and r['role'] == 'select' for r in rows.values()), rows)


def _bare_atom_kind(atom):
    from cmod.custom import targets as T
    return T._atom_requirement_kind(atom)

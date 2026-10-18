"""
@module cmod.objects.cmod.IsotopeVariant

IsotopeVariant - one class per file (design section 7). MISSION_PROFILE_SOLVER_PLAN.md section 8.3 (iso-0).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class IsotopeVariant(treeObject):
    """What it is: one WAY to do an `AtomJob` - one route (a plain GPIO poll, an external interrupt, a pin-change interrupt, an analog threshold, a
    shift register on SPI, an I2C expander ...). Hardware-agnostic: it says which pin profiles it needs (the `board.custom.target_compat.TASK_KINDS`
    kinds, with counts and roles), which on-chip peripherals it claims, which extra parts it needs, the lowest runtime tier it runs at, and its cost.
    The row holds only what is DECLARED or ESTIMATED: the stored `cost_json` entries are `estimated` (with their basis) or `undetermined`. What
    comes from what exists is worked out when asked and has no field here, on purpose: the status (declared, template-exists, compiles,
    proven-on-twin, proven-on-hardware), whether each part is on the bench, the measured costs of an implementation, and the eligibility on a board.
    A wasteful route stays a row: the attempt engine scores it worse, it never hides it.
    Related concepts: `AtomJob`, `CFunctionAtom`, `CIsotope`, `board.custom.kit_parts` (the bench), `board.custom.target_compat` (the pin-profile kinds).
    """

    plain_words = ('An isotope variant is one way of doing a firmware job - for example reading a button by watching the pin, by an interrupt, or '
                   'through a shift register. It says which pins, chip blocks and extra parts that way needs, what it costs, and how far it has got.')

    MINIMUM_LEVELS = ('bare-c', 'freertos', 'esp-idf', 'zephyr')   # cmod.custom.code_interface.LEVEL_ORDER (checked by the selftest)
    STATUSES = ('declared', 'template-exists', 'compiles', 'proven-on-twin', 'proven-on-hardware')   # weakest first
    COST_KEYS = ('pins', 'peripherals', 'parts', 'flash_bytes', 'ram_bytes', 'cpu_share', 'latency')
    COST_KINDS = ('measured', 'estimated', 'undetermined')

    @treeObjectInit
    def __init__(self, name: str = '', job: str = '', route: str = '', title: str = '', plain: str = '', profiles_json: str = '[]',
                 peripherals_json: str = '[]', parts_json: str = '[]', minimum_level: str = 'bare-c', cost_json: str = '{}',
                 wastefulness_note: str = '', implemented_by_json: str = '{}', citations_json: str = '[]', notes: str = '', manager=None):
        self.name = name                        # '<job>:<route>'
        self.job = job                          # the AtomJob name
        self.route = route                      # gpio-poll | ext-interrupt | ... (the route vocabulary of cmod.custom.isotope_variants_seeds.ROUTES)
        self.title = title
        self.plain = plain                      # the route in plain words
        self.profiles_json = profiles_json      # [{kind (TASK_KINDS), role, count, note}] - the pin profiles it needs
        self.peripherals_json = peripherals_json  # [{kind (on-chip block kind), why}]
        self.parts_json = parts_json            # [{class, kit_keys, terms, spec, why}] - on_bench is DERIVED from the KitPart rows when asked
        self.minimum_level = minimum_level      # bare-c | freertos | esp-idf | zephyr (the runtime ladder)
        self.cost_json = cost_json              # {pins|peripherals|parts|flash_bytes|ram_bytes|cpu_share|latency: {kind: estimated|undetermined, value, unit, basis}}
        self.wastefulness_note = wastefulness_note  # plain words: when this route is a poor default, and when it is the only one left
        self.implemented_by_json = implemented_by_json  # {atoms: [CFunctionAtom names], config, proof_purposes: [...]} - checked against what exists when asked; {} = none
        self.citations_json = citations_json    # [{label, ref}]
        self.notes = notes

"""
@module pcb.objects.pcb.SchematicSymbol

SchematicSymbol — one class per file (design §7); kxc-1, the KiCad interchange plan (AI-Notes/plans/KICAD_INTERCHANGE_PLAN.md §3).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class SchematicSymbol(treeObject):
    """What it is: ONE PLACED SYMBOL INSTANCE of a schematic — R1 on the root sheet, or U2 on the second instance of a child sheet
    used twice (KiCad keeps one symbol in the child file and gives each sheet instance its own reference; the walk is by instance,
    so both are rows). Its identity is the symbol's uuid + the sheet instance path (uuids from the root); the reference is a label.
    Carries everything KiCad stores on it: library id, unit, value, footprint, position / rotation / mirror, the BOM / board / DNP /
    simulation flags, EVERY property (properties_json), and the simulation fields split out (Sim.Device, Sim.Type, Sim.Name,
    Sim.Params, Sim.Pins, Sim.Library) — the inputs kxc-3 turns into simulation models — and any Polari.* properties (polari_json: what a Polari
    export encoded where KiCad has no field, kxc-5b). Part rows group these into BOM lines.
    """

    @treeObjectInit
    def __init__(self, name: str = '', board: str = '', ref: str = '', unit: int = 1, lib_id: str = '', value: str = '',
                 footprint: str = '', uuid: str = '', instance_path: str = '', sheet: str = '', file: str = '', x_mm: float = 0.0,
                 y_mm: float = 0.0, rotation: float = 0.0, mirror: str = '', in_bom: str = 'yes', on_board: str = 'yes', dnp: str = 'no',
                 exclude_from_sim: str = 'no', power: str = 'no', properties_json: str = '{}', sim_device: str = '', sim_type: str = '',
                 sim_name: str = '', sim_params: str = '', sim_pins: str = '', sim_library: str = '', polari_json: str = '{}', notes: str = '', manager=None):
        self.name = name  # board:ref:unit
        self.board = board
        self.ref = ref  # this instance's reference (R1, #PWR03)
        self.unit = unit  # the unit of a multi-unit part (U1 A = 1)
        self.lib_id = lib_id  # lib:symbol (a Symbol row)
        self.value = value
        self.footprint = footprint  # as named on the schematic
        self.uuid = uuid  # the symbol's own uuid in its file
        self.instance_path = instance_path  # /<root uuid>[/<sheet uuid>...] — KiCad's instance path
        self.sheet = sheet  # the same path by sheet names (/ampli_ht_vert/)
        self.file = file  # the .kicad_sch it sits in
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.rotation = rotation
        self.mirror = mirror  # '' | x | y
        self.in_bom = in_bom
        self.on_board = on_board
        self.dnp = dnp
        self.exclude_from_sim = exclude_from_sim
        self.power = power  # yes for a power symbol / flag (#PWR, #FLG)
        self.properties_json = properties_json  # every (property "K" "V") except the Sim.* six
        self.sim_device = sim_device
        self.sim_type = sim_type
        self.sim_name = sim_name
        self.sim_params = sim_params
        self.sim_pins = sim_pins
        self.sim_library = sim_library
        self.polari_json = polari_json  # kxc-5b: the hidden Polari.* properties a Polari export wrote (identity, drive, firmware) - read back on ingest
        self.notes = notes

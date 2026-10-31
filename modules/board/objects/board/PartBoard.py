"""
PartBoard - one class per file (design section 7); drv-0 / drv-1 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class PartBoard(treeObject):
    """What it is: A SINGLE PART OR SMALL MODULE, DEFINED BY ITS PINS AND THEIR DRIVE CONTRACT, THAT CAN SIT ON THE BENCH AS A BOARD - a driver that
    corrects drive (a Darlington array, a level shifter, a buffer, a gate or LED driver, a regulator or converter), a load (a motor, a relay coil, a
    lamp), or any module someone wants to define. The user's words (2026-10-31): drivers "as a type of component we can put into place to fix issues
    with drive", and "that way we can define custom drivers like mini boards and enable placing boards with footprints onto other boards".
    On the Bench it is the definition kind `part`: its footholds come from `pins_json` (board.custom.part_boards), so the bench net checks read it
    like any other Board, and it mounts onto another Board by position (board.custom.bench_mount: a DIP across a breadboard's trench, a breakout
    onto a PCB header footprint).
    `pins_json` [{number, name, role, channel, x_mm, y_mm}] - role in | out | supply | ground | common | nc; x / y in the part's own frame (top view,
    y down), from its package drawing (`position_basis` says which). The contract, per role, every number cited or -1 (not given):
      in       on_volts (the input voltage that turns a channel on), draw_ma (what an input draws when driven), in_max_v (absolute maximum)
      out      out_sink_ma / out_source_ma (what an output can sink / source; 0 is a real value - an open collector sources nothing), out_max_v
      supply   supply_min_v / supply_max_v; total_ma = the part's budget across all channels (e.g. a common emitter's total current)
      regulated  (drv-2, a converter's output) out_volts at up to out_source_ma - on the Bench a supply at out_volts; for a logic output out_volts is
               the level it drives high (V_OH)
    A pin may override its role's numbers (pins_json keys on_volts, draw_ma, max_volts, source_ma, sink_ma, logic_volts - a TLC5916's SDO is not its
    120 mA sinks; a regulator's input has its own minimum). `needs` = what the part needs around it to work, in words (a buck's inductor and diode).
    Rated temperatures (t_min_c / t_max_c) and the part's own ESD ratings (esd_hbm_v / esd_cdm_v) feed the temperature and ESD views.
    `origin`: cited (a datasheet: document, page_table, url) | custom (a person's definition, said as such).
    Related concepts: `BoardFoothold` (what the Bench sees), `BenchBoard` (a placed one), `BenchConnection` (kind mounted: its pins landed on another
    Board), `PartTemperatureBehaviour`, `PartThermalModel`.
    """

    plain_words = 'A single part or small module - a driver, a load, a breakout - described by its pins, that you can place on the bench.'

    KINDS = ('darlington-array', 'level-shifter', 'buffer', 'gate-driver', 'led-driver', 'high-side-switch', 'low-side-switch', 'ldo', 'buck',
             'boost', 'load', 'module')
    ROLES = ('in', 'out', 'supply', 'ground', 'common', 'nc', 'regulated')

    @treeObjectInit
    def __init__(self, name: str = '', kind: str = '', part_number: str = '', package: str = '', channels: int = 0, pins_json: str = '[]',
                 on_volts: float = -1.0, draw_ma: float = -1.0, in_max_v: float = -1.0, out_sink_ma: float = -1.0, out_source_ma: float = -1.0,
                 out_max_v: float = -1.0, supply_min_v: float = -1.0, supply_max_v: float = -1.0, total_ma: float = -1.0, t_min_c: float = -300.0,
                 t_max_c: float = -300.0, esd_hbm_v: float = -1.0, esd_cdm_v: float = -1.0, out_volts: float = -1.0, needs: str = '',
                 position_basis: str = '', contract_basis: str = '',
                 document: str = '', page_table: str = '', url: str = '', origin: str = 'custom', notes: str = '', manager=None):
        self.name = name                    # 'uln2003a-n' - the definition name on the Bench (part/<name>)
        self.kind = kind                    # one of KINDS
        self.part_number = part_number
        self.package = package              # 'PDIP-16 (TI N)'
        self.channels = channels
        self.pins_json = pins_json          # [{number, name, role, channel, x_mm, y_mm}]
        self.on_volts = on_volts            # input: the voltage that turns a channel on (-1 = not given)
        self.draw_ma = draw_ma              # input: what it draws when driven
        self.in_max_v = in_max_v            # input: absolute maximum
        self.out_sink_ma = out_sink_ma      # output: what it can sink
        self.out_source_ma = out_source_ma  # output: what it can source (0 = sources nothing)
        self.out_max_v = out_max_v          # output: absolute maximum
        self.supply_min_v = supply_min_v
        self.supply_max_v = supply_max_v
        self.total_ma = total_ma            # the budget across all channels
        self.t_min_c = t_min_c              # rated operating range (-300 = not given: 0 C is a real value)
        self.t_max_c = t_max_c
        self.esd_hbm_v = esd_hbm_v          # its own ESD rating, human body model (-1 = not given)
        self.esd_cdm_v = esd_cdm_v          # charged device model
        self.out_volts = out_volts          # drv-2: a regulated output's voltage, or a logic output's driven-high level (-1 = not given)
        self.needs = needs                  # drv-2: what it needs around it to work ('' = nothing)
        self.position_basis = position_basis  # where the pin positions come from (the package drawing)
        self.contract_basis = contract_basis  # where each contract number comes from, in words
        self.document = document
        self.page_table = page_table
        self.url = url
        self.origin = origin                # cited | custom
        self.notes = notes

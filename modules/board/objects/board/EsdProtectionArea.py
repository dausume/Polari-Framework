"""
EsdProtectionArea - one class per file (design section 7); esd-0 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class EsdProtectionArea(treeObject):
    """What it is: A PIECE OF A BOARD FLAGGED AS AN ESD PROTECTION AREA - a net, a foothold or a part's pins that must survive an electrostatic discharge.
    The user's words (2026-10-31): "we also need to be able to flag different pieces as ESD protection areas, which we need to establish simulations
    for testing where we emulate ESD events and check that the drive conditions handle it smoothly and do not break the circuits".
    It lives on the Board's DEFINITION (any kind: datasheet, geometry, layers, part - D-esd-3), so every bench that uses the board sees it.
    `scope` net | foothold | part and `target` (the net name, the foothold, the part ref); `inject_net` = where the discharge enters ('' = the target
    net itself, or the foothold's net); `protection_refs` = the parts that protect it (TVS diodes, varistors - refs, e.g. Z1, Z2).
    `protection_parts` (esd-3) = catalogue ProtectionParts (board.custom.protection_parts) the event places from the injected net to ground, each
    checked against its cited peak pulse current.
    The test: `model` (hbm = ANSI/ESDA/JEDEC JS-001, 100 pF / 1.5 kOhm; iec-contact = IEC 61000-4-2, 150 pF / 330 Ohm; iec-contact-waveform = the standard's own
    current equation - pcb.custom.esd_events.MODELS)
    at `level_v`. "Do not break": every protected node's peak against `abs_max_v` (the protected pins' absolute maximum, cited - -1 = not given, and
    the check then says undetermined). "Handle it smoothly": every protected node back within max(recover_pct % of the no-event run, recover_mv) by
    recover_us after the event (D-esd-2's knob, default 5 % / 50 mV / 10 us).
    esd-5: on a board with no simulated circuit a foothold area runs on the pin alone (board.custom.esd_footholds) with two knobs, `pin_cap_pf`
    (the chip pin's capacitance - replace it with the datasheet's C_IN) and `hold_ohm` (what holds the pin at its level).
    Related concepts: `BoardFoothold`, `SpiceRun` (the event run and its no-event baseline), `PartBoard` (a part's own ESD ratings).
    """

    plain_words = 'A part of a board that must survive a static shock, and what "survive" means for it.'

    SCOPES = ('net', 'foothold', 'part')

    @treeObjectInit
    def __init__(self, name: str = '', definition_kind: str = '', definition: str = '', scope: str = 'net', target: str = '', inject_net: str = '',
                 protection_refs: str = '', protection_parts: str = '', model: str = 'hbm', level_v: float = 2000.0, abs_max_v: float = -1.0, recover_pct: float = 5.0,
                 recover_mv: float = 50.0, recover_us: float = 10.0, pin_cap_pf: float = 10.0, hold_ohm: float = 1e6, document: str = '', page_table: str = '', origin: str = 'flagged on the page',
                 notes: str = '', manager=None):
        self.name = name                    # '<kind>:<definition>:<scope>:<target>'
        self.definition_kind = definition_kind
        self.definition = definition
        self.scope = scope                  # net | foothold | part
        self.target = target                # the net name / foothold / part ref
        self.inject_net = inject_net        # where the discharge enters ('' = derived from the target)
        self.protection_refs = protection_refs  # comma list of the protecting parts (TVS, varistor)
        self.protection_parts = protection_parts  # esd-3: comma list of catalogue ProtectionParts the event places from the net to ground
        self.model = model                  # hbm | iec-contact | iec-contact-waveform
        self.level_v = level_v              # the test level, V
        self.abs_max_v = abs_max_v          # the protected pins' absolute maximum, V (-1 = not given)
        self.recover_pct = recover_pct      # recovery: within this % of the no-event run ...
        self.recover_mv = recover_mv        # ... or this many mV, whichever is larger ...
        self.recover_us = recover_us        # ... by this long after the event
        self.pin_cap_pf = pin_cap_pf        # esd-5 knob: the chip pin's capacitance (a foothold event on a board with no circuit)
        self.hold_ohm = hold_ohm            # esd-5 knob: what holds the pin at its level
        self.document = document            # where abs_max_v comes from
        self.page_table = page_table
        self.origin = origin
        self.notes = notes

"""
ProtectionPart - one class per file (design section 7); esd-3 (AI-Notes/plans/DRIVERS_AND_ESD_PLAN.md).
"""
from objectTreeDecorators import treeObject, treeObjectInit


class ProtectionPart(treeObject):
    """What it is: A PART THAT PROTECTS A NET FROM A STATIC SHOCK - a TVS diode, a varistor, a polymer suppressor - with its datasheet's ratings.
    The user's words (2026-10-31): "flag different pieces as ESD protection areas ... check that the drive conditions handle it smoothly and do not break
    the circuits". An ESD area names the ones it uses (`EsdProtectionArea.protection_parts`); the event then places each from the protected net to ground
    and measures the current it carries against its rating.
    `kind` tvs-uni | tvs-bi | polymer | varistor. Ratings (-1 = not given): v_rwm (working voltage), v_br_min / v_br_max at i_t_ma (breakdown), v_c_v at
    i_pp_a for the pulse `pulse` (clamping; at i_c_a instead when that is given - a varistor's), v_f_v at i_f_a (forward, unidirectional), v_trigger_v
    (polymer / snapback), cap_pf.
    The SPICE model is DERIVED from those numbers (board.custom.protection_parts.spice_model), or refused in words when the device does not behave like
    the derivation assumes (a snapback polymer is not a breakdown diode).
    Related concepts: `EsdProtectionArea`, `SpiceRun`.
    """

    plain_words = 'A part that soaks up a static shock before it reaches the chip, and how much it can take.'

    KINDS = ('tvs-uni', 'tvs-bi', 'polymer', 'varistor')

    @treeObjectInit
    def __init__(self, name: str = '', kind: str = 'tvs-uni', part_number: str = '', package: str = '', v_rwm: float = -1.0, v_br_min: float = -1.0,
                 v_br_max: float = -1.0, i_t_ma: float = -1.0, v_c_v: float = -1.0, i_pp_a: float = -1.0, pulse: str = '', v_f_v: float = -1.0,
                 i_f_a: float = -1.0, v_trigger_v: float = -1.0, cap_pf: float = -1.0, t_min_c: float = -300.0, t_max_c: float = -300.0,
                 model_basis: str = '', document: str = '', page_table: str = '', url: str = '', origin: str = 'custom', notes: str = '',
                 i_c_a: float = -1.0, manager=None):
        self.name = name                # catalogue key, e.g. smbj5.0a
        self.kind = kind                # tvs-uni | tvs-bi | polymer | varistor
        self.part_number = part_number
        self.package = package
        self.v_rwm = v_rwm              # working peak reverse voltage, V
        self.v_br_min = v_br_min        # breakdown voltage at i_t_ma, V
        self.v_br_max = v_br_max
        self.i_t_ma = i_t_ma            # the breakdown test current, mA
        self.v_c_v = v_c_v              # clamping voltage at i_pp_a, V
        self.i_pp_a = i_pp_a            # peak pulse current for `pulse`, A
        self.pulse = pulse              # the pulse the clamping pair is rated at (e.g. 8/20 us)
        self.v_f_v = v_f_v              # forward voltage at i_f_a (unidirectional), V
        self.i_f_a = i_f_a
        self.v_trigger_v = v_trigger_v  # a snapback device's trigger voltage, V
        self.cap_pf = cap_pf            # capacitance, pF
        self.t_min_c = t_min_c
        self.t_max_c = t_max_c
        self.model_basis = model_basis  # which numbers the SPICE model is derived from, in words
        self.document = document
        self.page_table = page_table
        self.url = url
        self.origin = origin            # cited | custom
        self.notes = notes
        self.i_c_a = i_c_a              # esd-6: the current v_c_v is given at when it is not i_pp_a (a varistor: v_c at i_c, i_pp its surge rating); -1 = i_pp_a

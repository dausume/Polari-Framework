"""
@module reticulum.objects.device_catalog.DeviceModel

Row class DeviceModel of the reticulum module — one class per file (design §7), split
from device_catalog_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class DeviceModel(treeObject):
    """A device KIND: vendor lineage, openness, interop, radio facts
    and restrictions, each with evidence. The catalog answers 'what
    is this thing and what must I know before using it'."""

    @treeObjectInit
    def __init__(self, name='', display_name='', vendor='',
                 oem_vendor='', oem_model='', device_class='unknown',
                 radio_chip='', freq_mhz_lo=0.0, freq_mhz_hi=0.0,
                 tx_power_dbm_max=0, rx_sensitivity_dbm=0.0,
                 declared_range_m=0.0, declared_range_min_m=0.0,
                 declared_range_max_m=0.0, price_usd=0.0,
                 firmware_openness='unstated',
                 protocol_openness='unstated', config_protocol='',
                 interop='unknown', firmware_license='',
                 tool_license='', status='unevaluated',
                 restrictions_json='[]', setup_steps_json='[]',
                 evidence_json='[]', fidelity='declared', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        # Who sells it vs who actually makes it — rebadges are the
        # norm and the OEM's manual is usually the real documentation.
        self.vendor = vendor
        self.oem_vendor = oem_vendor
        self.oem_model = oem_model
        self.device_class = device_class
        self.radio_chip = radio_chip
        self.freq_mhz_lo = freq_mhz_lo
        self.freq_mhz_hi = freq_mhz_hi
        self.tx_power_dbm_max = tx_power_dbm_max
        # link-budget facts meshsim's flat_range_m() reads (§5p):
        # 0.0 = unstated, and the simulator refuses to guess.
        self.rx_sensitivity_dbm = rx_sensitivity_dbm
        # vendor-declared usable range, when one was stated —
        # preferred over derived link-budget math (fidelity).
        self.declared_range_m = declared_range_m
        # the vendor's SPAN when one was stated (SH-L1A: "0.5-1.5 km
        # depending on antenna") — the pessimistic/optimistic range
        # scenarios read these; 0 = unstated.
        self.declared_range_min_m = declared_range_min_m
        self.declared_range_max_m = declared_range_max_m
        # unit price for the placement/cost solvers (§5q). 0.0 =
        # UNSTATED and the solvers REFUSE to cost it — a plan priced
        # on a guess is worse than no plan. Date the evidence: prices
        # move.
        self.price_usd = price_usd
        self.firmware_openness = firmware_openness
        self.protocol_openness = protocol_openness
        # How it is configured ('e220-registers', 'rnodeconf', 'at').
        self.config_protocol = config_protocol
        self.interop = interop
        # Licence facts for anything we would run/flash/link — ''
        # means not applicable or not yet checked (say which in notes).
        self.firmware_license = firmware_license
        self.tool_license = tool_license
        self.status = status
        # [{kind, detail}] — the caveats an operator MUST read:
        # regulatory, buffering, certification, interop traps.
        self.restrictions_json = restrictions_json
        # [{step, detail}] — the physical/manual steps THIS kind of
        # device needs that software cannot do (switch positions,
        # button holds, replug requirements). Learned the hard way;
        # recorded so nobody re-learns.
        self.setup_steps_json = setup_steps_json
        # [{fact, source}] — where each load-bearing fact came from.
        self.evidence_json = evidence_json
        self.fidelity = fidelity
        self.notes = notes

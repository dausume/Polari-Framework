"""
@module reticulum.device_catalog_basis

The DEVICE CATALOG (Dustin 2026-08-13): what a KIND of device IS —
who makes it, who REALLY makes it (rebadges are the norm), how open
its firmware and protocol are, what it refuses to talk to, and the
restrictions an operator must know before keying it up. Prompted by
the SH-L1A bring-up, where every one of those facts was invisible
from the USB descriptor and material to legality and interop.

The idiom is the mesh-asset licence gate's: facts are STATED or the
row refuses to vouch — an unstated openness field is not "probably
fine", it is unstated. Every fact carries evidence (links, manual
sections, measurements) in evidence_json, and fidelity says whether
a number was declared by a vendor or measured by us.

One treeObject:

  DeviceModel   a product/kind row. DeviceLink (operator_basis)
                instances point at it via device_model_name — the
                catalog answers "what is this thing", the link row
                answers "which one is plugged in where".

@consumers reticulum.reticulum_api, DeviceLink rows
@see modules/reticulum/operator_basis.py (DeviceLink),
     modules/meshassets (the licence-gated catalog precedent)
"""

import json

from objectTreeDecorators import treeObject, treeObjectInit

#: What kind of communication device a model is. Extend as kinds
#: arrive; 'unknown' stays first-class (an unrecognized device is
#: reported unknown, never guessed — the DeviceLink rule).
DEVICE_CLASS_VALUES = ('lora-transparent-modem', 'lora-rnode-board',
                       'lorawan-module', 'sdr-rx', 'sdr-tx',
                       'wifi-adapter', 'halow-adapter', 'serial-kiss',
                       'unknown')

#: Openness of a device's FIRMWARE: can we read/replace what runs on
#: it? 'flashable-open' = proprietary as shipped but an open firmware
#: exists (the RNode path).
FIRMWARE_OPENNESS_VALUES = ('open-source', 'flashable-open',
                            'proprietary', 'unstated')

#: Openness of the CONTROL/WIRE protocol: 'documented' (vendor
#: publishes it), 'documented-via-oem' (the rebadger doesn't, the OEM
#: does — the SH-L1A case), 'reverse-engineered', 'undocumented'.
PROTOCOL_OPENNESS_VALUES = ('documented', 'documented-via-oem',
                            'reverse-engineered', 'undocumented',
                            'unstated')

#: Who a model can talk to over the air. 'closed-same-model' is the
#: SH-L1A case: pairs only — fine when both ends are ours, a trap
#: when someone expects RNode interop in the field.
INTEROP_VALUES = ('open-standard', 'closed-same-model', 'unknown')

#: Catalog verdict, meshassets-style. 'usable-with-caveats' means the
#: restrictions_json is REQUIRED reading before deployment.
MODEL_STATUS_VALUES = ('usable', 'usable-with-caveats', 'blocked',
                       'unevaluated')


def model_vouches(model):
    """Whether a catalog row can VOUCH for a model: openness and
    interop must be STATED and status must not be blocked/unevaluated.
    Returns (ok, reason). The meshassets usable() shape: unstated
    fields refuse — a catalog that guesses is worse than none."""
    status = model.get('status', 'unevaluated')
    if status in ('blocked', 'unevaluated'):
        return (False, 'status is %r — not vouched' % status)
    for field, unstated in (('firmware_openness', 'unstated'),
                            ('protocol_openness', 'unstated'),
                            ('interop', 'unknown')):
        if model.get(field, unstated) == unstated:
            return (False, '%s is %s — stated facts only, no '
                           'guessing' % (field, unstated))
    return (True, '')


def interop_possible(model_a, model_b):
    """Can two catalog models talk over the air? Pure rule for `.arch`
    bearer planning. Unknown refuses with the reason — a link plan
    built on 'probably' fails in the field."""
    ia, ib = model_a.get('interop', 'unknown'), \
        model_b.get('interop', 'unknown')
    if ia == 'unknown' or ib == 'unknown':
        return (False, 'interop unknown for %s' % (
            model_a.get('name') if ia == 'unknown'
            else model_b.get('name')))
    if ia == 'open-standard' and ib == 'open-standard':
        return (True, '')
    if ia == 'closed-same-model' or ib == 'closed-same-model':
        same = model_a.get('name') == model_b.get('name')
        return (same, '' if same else
                'closed framing: %s only talks to its own model'
                % (model_a.get('name') if ia == 'closed-same-model'
                   else model_b.get('name')))
    return (True, '')


class DeviceModel(treeObject):
    """A device KIND: vendor lineage, openness, interop, radio facts
    and restrictions, each with evidence. The catalog answers 'what
    is this thing and what must I know before using it'."""

    @treeObjectInit
    def __init__(self, name='', display_name='', vendor='',
                 oem_vendor='', oem_model='', device_class='unknown',
                 radio_chip='', freq_mhz_lo=0.0, freq_mhz_hi=0.0,
                 tx_power_dbm_max=0, rx_sensitivity_dbm=0.0,
                 declared_range_m=0.0, firmware_openness='unstated',
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


#: The first evidence-backed row: the SH-L1A pair bought for ret-6,
#: catalogued the day its facts were established (product page + OEM
#: manual + config-tool disassembly + our own measurements).
SEED_DEVICE_MODELS = [
    {
        'name': 'dsd-tech-sh-l1a',
        'display_name': 'DSD TECH SH-L1A USB LoRa adapter (SH-LM10A '
                        'module)',
        'vendor': 'DSD TECH',
        'oem_vendor': 'EByte',
        'oem_model': 'E220-900T22 (register-protocol identical; '
                     'OTA interop with genuine EByte unverified)',
        'device_class': 'lora-transparent-modem',
        'radio_chip': 'Semtech LLCC68',
        'freq_mhz_lo': 850.125,
        'freq_mhz_hi': 930.125,
        'tx_power_dbm_max': 22,
        'rx_sensitivity_dbm': -129.0,
        # vendor states 0.5-1.5 km depending on antenna — mid value;
        # the spread is the antenna's, the row records the middle.
        'declared_range_m': 1000.0,
        'firmware_openness': 'proprietary',
        'protocol_openness': 'documented-via-oem',
        'config_protocol': 'e220-registers (C0/C1/C2 at 9600 8N1 in '
                           'Config switch position; no AT set)',
        'interop': 'closed-same-model',
        'firmware_license': '',
        'tool_license': 'proprietary (DSD TECH Lora.exe, rebadged '
                        'EByte RF_Setting)',
        'status': 'usable-with-caveats',
        'restrictions_json': json.dumps([
            {'kind': 'regulatory',
             'detail': 'EByte factory default channel 23 = 873.125 '
                       'MHz is OUTSIDE US 902-928 ISM; set CH 52-77 '
                       'before transmitting in the US. No FCC ID as '
                       'end product — compliance is the deployer\'s.'},
            {'kind': 'buffering',
             'detail': '400-byte internal buffer, no flow control: '
                       'back-to-back writes overflow and drop (killed '
                       'an RNS Resource transfer, 2026-08-13). Pace '
                       'writes or raise air rate; sub-packet default '
                       '200 B.'},
            {'kind': 'interop',
             'detail': 'Vendor states pairs only ("not with '
                       'third-party Lora products"). No RNode/'
                       'Meshtastic interop; plan .arch links '
                       'same-model on both ends.'},
            {'kind': 'identity',
             'detail': 'CP2102 serial is "0001" on every unit — two '
                       'sticks collide in /dev/serial/by-id; use '
                       'by-path (or reprogram one).'},
        ]),
        'setup_steps_json': json.dumps([
            {'step': 'enter config mode',
             'detail': 'UNPLUG the stick, slide the side switch to '
                       'Config, replug — the switch drives the '
                       'module\'s M0/M1 pins and the clean way to '
                       'apply it is across a power cycle (verified '
                       'on the pair 2026-08-13). Registers then '
                       'answer at 9600 8N1.'},
            {'step': 'return to transparent mode',
             'detail': 'Unplug, slide back to RUN, replug. RUN is '
                       'the position for all actual traffic; in '
                       'Config nothing crosses the air.'},
            {'step': 'antenna',
             'detail': 'SMA antenna ON before any RUN-mode use — '
                       'a keyed LoRa PA without an antenna can '
                       'cook itself.'},
        ]),
        'evidence_json': json.dumps([
            {'fact': 'LLCC68, 850.125-930.125 MHz, 22 dBm, air rate '
                     '2.4k-62.5k',
             'source': 'https://www.deshide.com/product-details_'
                       'SH-L1A.html'},
            {'fact': 'E220 register protocol, defaults (9600 8N1, '
                     '2.4k air, CH23, 200B sub-packet), 400B buffer',
             'source': 'EByte E220-900T22D User Manual EN v1.0 + '
                       'disassembly of DSD config tool (RF_Setting '
                       'E220 internals) 2026-08-13'},
            {'fact': 'both-ways transparent link at 9600 8N1; frames '
                     'to 500 B intact singly; RNS link established, '
                     '56 B RTT ~2.2 s at factory settings',
             'source': 'measured on the owned pair, pol-core desk, '
                       '2026-08-13 (fidelity: measured-real)'},
            {'fact': 'register file read on BOTH owned units: shipped '
                     'exactly EByte defaults incl. CH23 = 873.125 MHz '
                     '(out of US ISM); reconfigured PERSISTENT to '
                     'CH65 = 915.125 MHz + 62.5k air, verified by '
                     're-read (raw 00 00 67 00 41 03 00 00)',
             'source': 'C1/C0 register transactions in Config mode, '
                       '2026-08-13 (fidelity: measured-real)'},
        ]),
        'fidelity': 'measured-real',
        'notes': 'The ret-6 desk pair. Reticulum path = '
                 'SerialInterface over transparent mode (no RNode '
                 'flash possible or needed).',
    },
]

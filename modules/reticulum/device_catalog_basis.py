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
                       'ham-transceiver', 'ham-receiver',
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
        'declared_range_min_m': 500.0,
        'declared_range_max_m': 1500.0,
        'price_usd': 27.99,
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
            {'fact': 'price_usd 27.99 — APPROXIMATE: Amazon listing '
                     'B0C7ZR4YBT would not render a price to a '
                     'non-browser fetch on 2026-08-13; taken from '
                     'the ~$25-30 range the earlier research '
                     'reported. Re-check before purchasing at scale.',
             'source': 'https://www.amazon.com/dp/B0C7ZR4YBT '
                       '(fidelity: declared, dated 2026-08-13)'},
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

#: REFERENCE CLASSES (§5q, Dustin 2026-08-13): typical per-scenario
#: range figures for PLANNING, researched with sources — not
#: purchasable SKUs. min = dense urban, typical = suburban,
#: max = rural/line-of-sight. Openness fields stay 'unstated' on
#: purpose: a reference row must never vouch (model_vouches refuses
#: it, correctly).
_REFERENCE_NOTE = ('REFERENCE CLASS — typical figures for planning, '
                   'not a purchasable SKU; replace with a real model '
                   'row before buying. Openness deliberately '
                   'unstated: reference rows do not vouch.')

SEED_DEVICE_MODELS += [
    {
        'name': 'generic-lora',
        'display_name': 'Generic LoRa node (sub-GHz, reference)',
        'vendor': '(reference class)',
        'device_class': 'lora-transparent-modem',
        'radio_chip': '(class: SX12xx/LLCC68-family)',
        'declared_range_min_m': 2000.0,
        'declared_range_m': 5000.0,
        'declared_range_max_m': 15000.0,
        'price_usd': 0.0,
        'status': 'usable-with-caveats',
        'restrictions_json': json.dumps([
            {'kind': 'planning',
             'detail': 'Vendor 15 km figures are tower-mounted '
                       'line-of-sight; dense urban reliably degrades '
                       'to the 2 km end. Antenna and elevation '
                       'dominate.'}]),
        'evidence_json': json.dumps([
            {'fact': 'urban 2-5 km typical; rural/LoS 10-20 km '
                     'reported in deployment practice',
             'source': 'https://tago.io/blog/lorawan-range-in-the-'
                       'real-world (fetched 2026-08-13); '
                       'https://yosensi.io/posts/what_is_the_real_'
                       'range_of_lora/'},
            {'fact': 'price left UNSTATED (0) on purpose — real SKUs '
                     'vary widely; the dsd-tech-sh-l1a row carries a '
                     'real dated price',
             'source': 'catalog policy 2026-08-13'}]),
        'fidelity': 'declared',
        'notes': _REFERENCE_NOTE,
    },
    {
        'name': 'generic-ham-vhf-uhf',
        'display_name': 'Generic HAM VHF/UHF station (reference)',
        'vendor': '(reference class)',
        'device_class': 'ham-transceiver',
        'radio_chip': '(class: VHF 2m / UHF 70cm FM/packet)',
        'declared_range_min_m': 3200.0,
        'declared_range_m': 24000.0,
        'declared_range_max_m': 48000.0,
        'price_usd': 0.0,
        'status': 'usable-with-caveats',
        'restrictions_json': json.dumps([
            {'kind': 'regulatory',
             'detail': 'TRANSMIT requires an amateur licence; '
                       'cleartext + public-only publication on '
                       'amateur interfaces (plan 5f/5g). RX-only '
                       'stations need nothing.'},
            {'kind': 'planning',
             'detail': 'min = handheld in dense urban (~2 mi); '
                       'typical = base antenna simplex (~15 mi); '
                       'max = elevated base/LoS (~30 mi). HF '
                       'skywave (100s-1000s km) is a DIFFERENT '
                       'regime, out of scope for these rows.'}]),
        'evidence_json': json.dumps([
            {'fact': 'handheld 2-5 mi simplex; 15-30 mi with '
                     'elevation/base antennas',
             'source': 'https://hamradioprep.com/ham-radio-range/ '
                       '(fetched 2026-08-13); https://www.'
                       'survivalsullivan.com/ham-radio-range-'
                       'distance/'},
            {'fact': 'price UNSTATED (0): a $25 handheld and a '
                     '$1000+ base station are both this class — '
                     'too wide a span to state one number honestly',
             'source': 'catalog policy 2026-08-13'}]),
        'fidelity': 'declared',
        'notes': _REFERENCE_NOTE,
    },
    {
        'name': 'generic-wifi-24',
        'display_name': 'Generic WiFi 2.4 GHz (stock omni, reference)',
        'vendor': '(reference class)',
        'device_class': 'wifi-adapter',
        'radio_chip': '(class: 802.11b/g/n 2.4 GHz)',
        'declared_range_min_m': 45.0,
        'declared_range_m': 90.0,
        'declared_range_max_m': 300.0,
        'price_usd': 0.0,
        'status': 'usable-with-caveats',
        'restrictions_json': json.dumps([
            {'kind': 'planning',
             'detail': 'Stock omnidirectional outdoors: 45-90 m '
                       'typical, ~300 m best-case with outdoor APs. '
                       'DIRECTIONAL point-to-point reaches km-scale '
                       'but is its own aimed-link case, not this '
                       'row.'}]),
        'evidence_json': json.dumps([
            {'fact': 'consumer 2.4 GHz 45-90 m outdoors; ~300 m '
                     'with outdoor APs; km-scale only directional',
             'source': 'https://epb.com/get-connected/gig-internet/'
                       'how-far-will-your-wi-fi-signal-reach/ '
                       '(fetched 2026-08-13); https://www.blackview.'
                       'hk/blog/guides/how-far-can-a-router-reach'},
            {'fact': 'price UNSTATED (0): $10 dongles to $200 APs',
             'source': 'catalog policy 2026-08-13'}]),
        'fidelity': 'declared',
        'notes': _REFERENCE_NOTE,
    },
    {
        'name': 'generic-wifi-halow',
        'display_name': 'Generic WiFi HaLow 802.11ah (reference)',
        'vendor': '(reference class)',
        'device_class': 'halow-adapter',
        'radio_chip': '(class: 802.11ah sub-GHz, e.g. Morse Micro '
                      'MM6108)',
        'declared_range_min_m': 1000.0,
        'declared_range_m': 3000.0,
        'declared_range_max_m': 16000.0,
        'price_usd': 134.97,
        'status': 'usable-with-caveats',
        'restrictions_json': json.dumps([
            {'kind': 'planning',
             'detail': 'min = ~1 km academic urban/23 dBm; typical = '
                       '3 km city field record (Morse Micro, Ocean '
                       'Beach SF); max = 16 km desert LoS at ~2 Mbps '
                       'UDP (Joshua Tree). The interesting middle '
                       'bearer: real bandwidth AND real range '
                       '(plan 5d).'}]),
        'evidence_json': json.dumps([
            {'fact': '3 km urban field demo 2024-01; 16 km / 2 Mbps '
                     'UDP LoS field test 2024-09',
             'source': 'https://www.morsemicro.com/2024/01/23/'
                       'morse-micro-demonstrates-worlds-longest-'
                       'range-wi-fi-halow-solution-reaching-3-'
                       'kilometers/ ; https://www.techradar.com/pro/'
                       'groundbreaking-wireless-tech-that-can-run-'
                       'on-coin-batteries-for-months-hits-new-'
                       'milestone-halow-achieves-10-mile-range-in-'
                       'latest-test (fetched 2026-08-13)'},
            {'fact': 'ALFA HaLow-U USB adapter $134.97',
             'source': 'https://store.rokland.com/products/alfa-'
                       'network-halow-u-802-11ah-halow-usb-adapter-'
                       'support-ap-client-mode (fetched 2026-08-13; '
                       'prices move — re-check before buying)'}]),
        'fidelity': 'declared',
        'notes': _REFERENCE_NOTE,
    },
]

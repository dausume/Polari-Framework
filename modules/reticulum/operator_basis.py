"""
@module reticulum.operator_basis

The operator + device surface (plan §5g item 1 and §5i/ret-2b).

  OperatorLicense  the operator's OWN ASSERTION that they hold a
                   licence — recorded, tied to a KC user, expiry
                   tracked and surfaced. THE ASSERTION IS THE ONLY
                   CHECK: nothing validates against an external
                   service, ever — a radio gated by an unreachable
                   server defeats an emergency tool. The software
                   holds the record, shows it, and says when it has
                   lapsed; it states NO legal conclusions.
  DeviceLink       an attached device as a row: bus ids, what we
                   think it IS, which interface it backs, which
                   VM/container owns it — measured facts separate
                   from declared. Detection degrades HONESTLY: an
                   unknown USB id is reported unknown with its ids
                   shown, never guessed into a capability.

@consumers reticulum.reticulum_api
@see modules/reticulum/reticulum_basis.py (INTERFACE_DIRECTION_VALUES —
     rx/tx is a device FACT), plan §5l (passthrough is a gated SHELL
     capability; the helper holds the privilege, never the shell)
"""

import datetime

from objectTreeDecorators import treeObject, treeObjectInit

#: Licence-record states the UI surfaces. 'none' and 'expired'
#: produce a clear WARNING naming what is missing — not a legal
#: verdict, and never a gate that would break the emergency case.
LICENSE_STATE_VALUES = ('none', 'valid', 'approaching-expiry',
                        'expired', 'undated')

#: What we think an attached device IS. 'unknown' is first-class.
DEVICE_KIND_VALUES = ('lora-board', 'wifi-adapter', 'halow-adapter',
                      'sdr-rx', 'sdr-tx', 'serial-kiss', 'unknown')

#: Who currently owns the device (host, or a named VM/container).
#: Passthrough is EXCLUSIVE — one device, one owner at a time (§5h).


def license_state(expiry_date_iso, today_iso, approach_days=60):
    """Pure expiry ladder: '' -> undated (recorded but no dates),
    else valid / approaching-expiry / expired by date arithmetic.
    A lapsed licence is the failure mode a busy operator will
    actually hit, so 'approaching' is a state, not a nicety."""
    if not expiry_date_iso:
        return 'undated'
    try:
        expiry = datetime.date.fromisoformat(expiry_date_iso)
        today = datetime.date.fromisoformat(today_iso)
    except ValueError:
        return 'undated'
    if today > expiry:
        return 'expired'
    if (expiry - today).days <= approach_days:
        return 'approaching-expiry'
    return 'valid'


def license_warning(state, callsign=''):
    """The warning text a surface shows for a licence state. Empty
    string when nothing needs saying. Names WHAT is missing; asserts
    nothing about any jurisdiction's law."""
    who = (' (%s)' % callsign) if callsign else ''
    if state == 'none':
        return ('no operator licence on file%s — transmit surfaces '
                'will warn; recording one is the operator\'s own '
                'assertion, never validated online' % who)
    if state == 'expired':
        return ('operator licence%s is past its recorded expiry — '
                'renew and update the row' % who)
    if state == 'approaching-expiry':
        return ('operator licence%s approaches its recorded expiry'
                % who)
    if state == 'undated':
        return ('operator licence%s has no expiry recorded — expiry '
                'tracking is off until dates are filled in' % who)
    return ''


def offers_transmit(direction):
    """§5i: a device that cannot transmit never offers a transmit
    control — honest UI, not a missing feature."""
    return direction in ('tx', 'both')


def describe_device(vendor_id, product_id, declared_kind):
    """Honest device description: a recognized declaration passes
    through; anything else is 'unknown' WITH its ids shown — never
    guessed into a capability."""
    if declared_kind in DEVICE_KIND_VALUES and declared_kind != 'unknown':
        return declared_kind
    return 'unknown (usb %s:%s)' % (vendor_id or '????',
                                    product_id or '????')


class OperatorLicense(treeObject):
    """A self-declaration with an author and a timestamp — precisely
    what it claims to be, and the software never pretends it is more.
    Identity stays Keycloak's: this row ANNOTATES a user."""

    @treeObjectInit
    def __init__(self, name='', kc_subject='', callsign='',
                 license_class='', issuing_authority='',
                 jurisdiction='', issued_date='', expiry_date='',
                 asserted_at='', notes='', manager=None):
        self.name = name
        self.kc_subject = kc_subject
        self.callsign = callsign
        self.license_class = license_class
        self.issuing_authority = issuing_authority
        self.jurisdiction = jurisdiction
        self.issued_date = issued_date
        self.expiry_date = expiry_date
        # When the operator made the assertion — part of the record.
        self.asserted_at = asserted_at
        self.notes = notes


class DeviceLink(treeObject):
    """An attached device, populated from real udev facts (§5j:
    by-id paths keep identity across replug). measured_direction is
    a DEVICE FACT (an RTL-SDR is rx because it cannot be otherwise);
    declared_kind is what a human says it is; the split is fidelity."""

    @treeObjectInit
    def __init__(self, name='', bus_id='', usb_vendor_id='',
                 usb_product_id='', by_id_path='',
                 device_model_name='', declared_kind='unknown',
                 measured_direction='', interface_name='',
                 owner='host', needs_firmware_flash=False,
                 fidelity='declared', notes='', manager=None):
        self.name = name
        self.bus_id = bus_id
        self.usb_vendor_id = usb_vendor_id
        self.usb_product_id = usb_product_id
        self.by_id_path = by_id_path
        # The catalog row (DeviceModel) this instance is one of —
        # the catalog answers WHAT it is, this row answers WHICH and
        # WHERE. ⚠ by-id collides on identical-serial bridges (the
        # SH-L1A case: every CP2102 is "0001") — by_id_path may be
        # empty and the PORT path is then the stable identity.
        self.device_model_name = device_model_name
        self.declared_kind = declared_kind
        # '' until measured — absence of a fact is not a fact.
        self.measured_direction = measured_direction
        self.interface_name = interface_name
        # Exclusive owner: 'host' or a named VM/container (§5h:
        # passthrough is exclusive; the shell helper enforces the
        # rows' correspondence rule, plan §5l).
        self.owner = owner
        # 'USB LoRa' dongles are dev boards wanting RNode firmware
        # (rnodeconf) before Reticulum can speak to them (§5h).
        self.needs_firmware_flash = needs_firmware_flash
        self.fidelity = fidelity
        self.notes = notes

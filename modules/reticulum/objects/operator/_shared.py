"""@module reticulum.objects.operator._shared — what the operator row classes share (constants, seeds, helpers); split from operator_basis.py (sap-2c)."""
import datetime

LICENSE_STATE_VALUES = ('none', 'valid', 'approaching-expiry',
                        'expired', 'undated')
DEVICE_KIND_VALUES = ('lora-board', 'wifi-adapter', 'halow-adapter',
                      'sdr-rx', 'sdr-tx', 'serial-kiss', 'unknown')
WIFI_ASSIGNMENT_VALUES = ('unassigned', 'reticulum', 'onboarding-ap',
                          'dual-one-network', 'dual-ap-sta',
                          'dual-switched')
def wifi_use_allowed(assignment, use, ap_sta_measured=False):
    """May a WiFi device serve `use` ('reticulum' | 'onboarding-ap')
    under its assignment? Returns (bool, reason). dual-ap-sta REFUSES
    until the chipset fact is measured; unassigned refuses both —
    assignment is deliberate."""
    if use not in ('reticulum', 'onboarding-ap'):
        return (False, 'unknown use %r' % (use,))
    if assignment == 'unassigned':
        return (False, 'device is unassigned — assign it first '
                       '(nothing claims a device silently)')
    if assignment in ('reticulum', 'onboarding-ap'):
        return (assignment == use,
                '' if assignment == use else
                'assigned %s-only' % assignment)
    if assignment == 'dual-one-network':
        return (True, '')
    if assignment == 'dual-ap-sta':
        if not ap_sta_measured:
            return (False, 'dual-ap-sta requires the MEASURED chipset '
                           'fact (iw interface combinations) — '
                           'unmeasured concurrency is a hope')
        return (True, '')
    if assignment == 'dual-switched':
        return (True, 'switched: activating %s interrupts the other '
                      'use — a deliberate act with provenance' % use)
    return (False, 'unknown assignment %r' % (assignment,))
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

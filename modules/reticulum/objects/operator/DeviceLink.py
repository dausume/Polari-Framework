"""
@module reticulum.objects.operator.DeviceLink

Row class DeviceLink of the reticulum module — one class per file (design §7), split
from operator_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

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
                 owner='host', wifi_assignment='unassigned',
                 ap_capable='', ap_sta_capable='',
                 needs_firmware_flash=False,
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
        # WiFi devices: what this device is FOR (the assignment knob,
        # WIFI_ASSIGNMENT_VALUES) + the two MEASURED chipset facts
        # ('' = unmeasured; 'yes'/'no' once iw list is ingested via
        # the isle agent — RETICULUM_ISLE_CORE_REQUEST items 5-6).
        self.wifi_assignment = wifi_assignment
        self.ap_capable = ap_capable
        self.ap_sta_capable = ap_sta_capable
        # 'USB LoRa' dongles are dev boards wanting RNode firmware
        # (rnodeconf) before Reticulum can speak to them (§5h).
        self.needs_firmware_flash = needs_firmware_flash
        self.fidelity = fidelity
        self.notes = notes

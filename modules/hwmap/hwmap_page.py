"""@module hwmap.hwmap_page — /display/hardware-map: devices, ports, slots, and what can be mapped to a KVM (tables + structured panels)."""
from polariApiServer.module_pages_seed import _page, _row, _sapi, _table

SEED_HWMAP_PAGE_DISPLAYS = [
    _page('hardware-map', 'hardware-map',
          'Hardware map: what each device has (ports, slots) and what can be mapped to a potential KVM — usb hostdev, pci vfio '
          '(IOMMU group of its own), nic macvtap — with the reasons, and which hardware apps each port satisfies. Rows come from '
          'pol hwmap push on the device; nothing here is assumed.',
          'HardwareMapSnapshot',
          [_row(0, [_sapi('hwmap-devices', 0, 6, 'Devices (hardware-tier readiness)', '/api/hwmap', pick='devices'),
                    _sapi('hwmap-candidates', 1, 6, 'What can be mapped (all devices)', '/api/hwmap/candidates', pick='candidates')]),
           _row(1, [_table('hwmap-ports', 0, 7, 'Ports', 'HardwarePort', columns='device_name,kind,role,port_id,description,driver,slot,owner,iommu_group'),
                    _table('hwmap-slots', 1, 5, 'Slots (controllers, hubs, bridges)', 'HardwareSlot', columns='device_name,kind,slot_id,driver,ports_used,ports_total,speed_mbps,parent')]),
           _row(2, [_table('hwmap-verdicts', 0, 12, 'Passthrough verdicts', 'PassthroughCandidate', columns='device_name,port,mapping,mappable,reasons_json,satisfies_json')])]),
]

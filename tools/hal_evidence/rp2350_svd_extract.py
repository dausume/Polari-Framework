"""rp2350_svd_extract - hal-4 proof 2 (econ, 2026-11-13): cut the GPIO path out of Raspberry Pi's RP2350.svd (pico-sdk 2.2.0,
BSD-3-Clause) so the repo carries only what the proof reads, with the vendor's copyright + SPDX header verbatim.

    python3 -I tools/hal_evidence/rp2350_svd_extract.py <RP2350.svd> <out.svd>

Kept: SIO GPIO_IN / GPIO_OUT{,_SET,_CLR,_XOR} / GPIO_OE{,_SET,_CLR,_XOR}; IO_BANK0 GPIO0..31_CTRL; PADS_BANK0 GPIO0..31.
Everything else (other peripherals, registers, the cpu block's interrupts) is dropped; the elements kept are copied unchanged.
"""
import copy
import hashlib
import sys
import xml.etree.ElementTree as ET

SOURCE = 'https://raw.githubusercontent.com/raspberrypi/pico-sdk/2.2.0/src/rp2350/hardware_regs/RP2350.svd'
SIO = {'GPIO_IN', 'GPIO_OUT', 'GPIO_OUT_SET', 'GPIO_OUT_CLR', 'GPIO_OUT_XOR', 'GPIO_OE', 'GPIO_OE_SET', 'GPIO_OE_CLR', 'GPIO_OE_XOR'}
KEEP = {'SIO': SIO, 'IO_BANK0': {'GPIO%d_CTRL' % n for n in range(32)}, 'PADS_BANK0': {'GPIO%d' % n for n in range(32)}}


def main(src, out):
    raw = open(src, 'rb').read()
    text = raw.decode('utf-8')
    head = text[text.index('<!--'):text.index('-->') + 3]
    if 'SPDX-License-Identifier: BSD-3-Clause' not in head:
        raise SystemExit('refused: the source header does not carry the BSD-3-Clause SPDX line')
    root = ET.fromstring(raw)
    dev = ET.Element(root.tag, root.attrib)
    for child in root:
        if child.tag != 'peripherals':
            dev.append(copy.deepcopy(child))
    pers = ET.SubElement(dev, 'peripherals')
    found = {}
    for p in root.find('peripherals'):
        name = p.findtext('name')
        if name not in KEEP:
            continue
        if p.get('derivedFrom'):
            raise SystemExit('refused: %s is derivedFrom %s (this extract does not carry its base)' % (name, p.get('derivedFrom')))
        q = copy.deepcopy(p)
        regs = q.find('registers')
        for r in list(regs):
            if r.tag != 'register' or r.findtext('name') not in KEEP[name]:
                regs.remove(r)
        for i in list(q.findall('interrupt')):
            q.remove(i)
        found[name] = sorted(r.findtext('name') for r in regs)
        pers.append(q)
    for name, want in KEEP.items():
        if set(found.get(name, ())) != want:
            raise SystemExit('refused: %s kept %s, expected %s' % (name, sorted(found.get(name, ())), sorted(want)))
    ET.indent(dev, space='    ') if hasattr(ET, 'indent') else None
    body = ET.tostring(dev, encoding='unicode')
    prov = ('<!--\n  EXTRACT (econ, hal-4 proof 2) of %s\n  source sha256 %s; kept: SIO GPIO_IN/OUT*/OE*, IO_BANK0 GPIO0..31_CTRL,\n'
            '  PADS_BANK0 GPIO0..31 (elements unchanged); regenerate with tools/hal_evidence/rp2350_svd_extract.py.\n-->\n'
            % (SOURCE, hashlib.sha256(raw).hexdigest()))
    open(out, 'w').write('<?xml version="1.0" encoding="utf-8"?>\n%s\n%s%s\n' % (head, prov, body))
    print('wrote %s: %s' % (out, {k: len(v) for k, v in found.items()}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

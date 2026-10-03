"""
@module board.custom.programmers

THE PROGRAMMER KINDS (plan §7a): programmer kind → engine → adapter kind → the DRY-RUN argv template. A template is
what the installer PRINTS before any real run (placeholders in braces); a real run needs the device present and an
explicit confirm (brd-1 / brd-fi). Every engine named here must pass RULE 2 (board_engines.rule2_ok).

`fpga-usb-jtag` is the one kind beyond the plan's list: the register's two open FPGA boards (iCEBreaker, ULX3S) are
flashed through their onboard FTDI over USB by openFPGALoader — neither OpenOCD's SWD route nor any other listed kind.
"""


def _pk(name, title, engine, kind, adapter_kind, template, licence, citation, notes=''):
    return {'name': name, 'title': title, 'engine': engine, 'engine_kind': kind, 'adapter_kind': adapter_kind,
            'host_side': 'usb', 'dry_run_template': template, 'placement': 'usb-host', 'needs_confirm': True,
            'licence': licence, 'citation': citation, 'notes': notes}


SEED_PROGRAMMER_KINDS = [
    _pk('avrdude-optiboot', 'avrdude to the Optiboot bootloader over USB-CDC', 'avrdude', 'flasher', '',
        'avrdude -p {mcu} -c arduino -P {port} -b {baud} -D -U flash:w:{artifact}:i',
        'GPL-2.0', 'plan §3 step 4; boards.txt uno.upload.protocol=arduino, upload.speed=115200'),
    _pk('esptool', 'esptool over the native USB-Serial/JTAG or an onboard USB-UART', 'esptool', 'flasher', '',
        'esptool.py --chip {chip} --port {port} --baud {baud} write_flash {offset} {artifact}',
        'GPL-2.0+', 'register §1 esp32-c3/c6/p4, lilygo, heltec, slimevr rows'),
    _pk('uf2', 'UF2 drag-and-drop to the bootloader mass-storage drive', 'uf2-copy', 'flasher', '',
        'cp {artifact} {mount}/', 'n/a (a file copy)', 'register §1 samd21/51, pico2, rp2040, nrf52840, rak rows',
        'picotool is optional for RP2040/RP2350'),
    _pk('dfu', 'USB DFU (the chip ROM bootloader)', 'dfu-util', 'flasher', '',
        'dfu-util -d {usb_id} -a {alt} -s {address}:leave -D {artifact}',
        'GPL-2.0+', 'register §1 longan-nano, stm32f4-discovery, stm32g4-libresolar rows; OrangeCrab (USB-C DFU)'),
    _pk('swd-probe', 'SWD/JTAG through a USB probe (OpenOCD)', 'openocd', 'flasher', 'usb-swd/jtag probe',
        'openocd -f interface/{interface}.cfg -f target/{target}.cfg -c "program {artifact} verify reset exit"',
        'GPL-2.0+', 'plan §7a; register §1a rpi-debug-probe / tigard / ftdi rows',
        'probe-rs is the alternative engine (licence check before admission)'),
    _pk('wch-isp', 'WCH ROM USB ISP bootloader (wchisp)', 'wchisp', 'flasher', '',
        'wchisp flash {artifact}', 'licence unverified (register §1 ch32v203)', 'register §1 ch32v203 row'),
    _pk('hss-usbdmsc', 'BeagleV-Fire eMMC as USB mass storage via the HSS console (USB-UART on the debug header)', 'dd', 'flasher', 'usb-uart',
        'console {console_port} 115200: <key> mmc usbdmsc ; then dd if={artifact} of={block_device} bs=4M conv=fsync status=progress',
        'coreutils', 'plan §4(a); D-brd-6 (inside the refined rule); register §1 beaglev-fire row [10]',
        'the console step is typed by a person or the brd-2 verb; the dd target is the "MCC PolarFireSoC_msd" device'),
    _pk('libero-gateware', 'Fire gateware applied FROM Linux over the USB-C network', 'change-gateware', 'flasher', '',
        'ssh {user}@{host} sudo /usr/share/beagleboard/gateware/change-gateware.sh {bitstream_dir}',
        'the bitstream is built by the libero engine (PROPRIETARY, D-brd-2) or BeagleBoard CI', 'plan §4(c)'),
    _pk('fpga-usb-jtag', 'FPGA bitstream over the onboard FTDI USB-JTAG (openFPGALoader)', 'openfpgaloader', 'flasher', '',
        'openFPGALoader -b {board} {artifact}', 'Apache-2.0', 'register §1 icebreaker-ice40-up5k, ulx3s-orangecrab-ecp5 rows',
        'beyond the plan §7a list — see the module docstring'),
]
PROGRAMMER_NAMES = {p['name'] for p in SEED_PROGRAMMER_KINDS}


def render_dry_run(programmer, **values):
    """The exact argv a DRY-RUN prints; a missing placeholder stays visible as {name} (never guessed)."""
    row = next((p for p in SEED_PROGRAMMER_KINDS if p['name'] == programmer), None)
    if row is None:
        raise KeyError(programmer)
    out = row['dry_run_template']
    for k, v in values.items():
        out = out.replace('{%s}' % k, str(v))
    return out

"""
@module board.custom.esp32c3_evidence

c3pf (FIRMWARE_GENERATION_MODULE_PLAN.md section 11): THE DOCUMENTS the ESP32-C3 pin-function rows cite - fetched and hashed 2026-10-18 (never typed from
memory; the PDFs themselves are NOT committed - licence and size - only the facts read from them, with document, revision, url, sha256 and page/table):

  * ESP32-C3 Series Datasheet v2.4       the SAME file board_c3 already cites (sha256 833fc000...f968, re-fetched, matched)
  * ESP32-C3 Technical Reference Manual  v1.4, 903 pages - the IO MUX and GPIO Matrix chapter (Table 5.11-1 the peripheral signal list, Table 5.12-1 the IO MUX
                                         list), the GPIO_PINn_REG interrupt field, the LED PWM and SAR ADC chapters
  * ESP32-C3-MINI-1 & MINI-1U Datasheet  v2.2 - the module on the DevKitM: its Table 3-1 pin definitions (which chip pins the module brings out; the flash
                                         pins are "NC") and "the flash is integrated in the chip's package"
  * ESP32-C3-DevKitM-1 user guide        (HTML, docs.espressif.com "latest") - the J1/J3 header tables, the boot button, the RGB LED on GPIO8, the USB-UART bridge

Page numbers are the printed page numbers (= the PDF page index in all three PDFs). The HTML guide has sections, not pages: it is cited by section/table name.
"""
from board.custom import board_c3 as C

DS_DOC, DS_REV, DS_URL = C.DS_DOC, C.DS_REV, C.DS_URL

TRM_SHA = '90ef825653e7a2657dc1bb294041aace9f9b69da87d775c2f1b5bd11eb317423'
TRM_DOC = 'Espressif ESP32-C3 Technical Reference Manual'
TRM_REV = 'v1.4 - fetched 2026-10-18, file sha256 %s' % TRM_SHA
TRM_URL = 'https://www.espressif.com/sites/default/files/documentation/esp32-c3_technical_reference_manual_en.pdf'

MINI_SHA = 'de7361381348d82a1abd337f10170be7a420675987568f71fe3c5b100deed270'
MINI_DOC = 'Espressif ESP32-C3-MINI-1 & MINI-1U Datasheet'
MINI_REV = 'v2.2 - fetched 2026-10-18, file sha256 %s' % MINI_SHA
MINI_URL = 'https://www.espressif.com/sites/default/files/documentation/esp32-c3-mini-1_datasheet_en.pdf'

KIT_SHA = 'e36f1ce3281546fd67072e10a02a016823f5000641bec8f8717a67d7b9d16b4a'
KIT_DOC = 'Espressif ESP32-C3-DevKitM-1 user guide'
KIT_REV = 'docs.espressif.com "latest" HTML page - fetched 2026-10-18, file sha256 %s' % KIT_SHA
KIT_URL = 'https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32c3/esp32-c3-devkitm-1/user_guide.html'

#: short key -> (document, revision, url)
DOCS = {'ds': (DS_DOC, DS_REV, DS_URL), 'trm': (TRM_DOC, TRM_REV, TRM_URL), 'mini': (MINI_DOC, MINI_REV, MINI_URL), 'kit': (KIT_DOC, KIT_REV, KIT_URL)}
SHORT = {'ds': 'ESP32-C3 datasheet v2.4', 'trm': 'ESP32-C3 TRM v1.4', 'mini': 'ESP32-C3-MINI-1 datasheet v2.2', 'kit': 'ESP32-C3-DevKitM-1 user guide'}
SOC = C.SOC
BOARD = C.BOARD


def fact(key, value, where, doc='ds', unit='', notes=''):
    """One DatasheetFact dict for the ESP32-C3 SoC (name 'esp32c3:<key>'), citing document + revision + url + page/table."""
    d, r, u = DOCS[doc]
    return {'name': '%s:%s' % (SOC, key), 'board': SOC, 'fact_key': key, 'value': str(value), 'unit': unit, 'document': d, 'revision': r, 'page_table': where,
            'url': u, 'notes': notes}


def board_fact(key, value, where, doc='kit', notes=''):
    """Same, named for the board ('esp32-c3:<key>')."""
    d, r, u = DOCS[doc]
    return {'name': '%s:%s' % (BOARD, key), 'board': BOARD, 'fact_key': key, 'value': str(value), 'unit': '', 'document': d, 'revision': r, 'page_table': where,
            'url': u, 'notes': notes}


def cite(doc, where):
    """The three citation columns every c3pf row carries."""
    d, _r, u = DOCS[doc]
    return {'document': d, 'page_table': where, 'url': u}


def board_facts():
    """DatasheetFact rows for the DevKitM-1 and its ESP32-C3-MINI-1 module (named 'esp32-c3:...')."""
    return [
        board_fact('devkit.header', 'J1: GND, 3V3, 3V3, IO2, IO3, GND, RST, GND, IO0, IO1, IO10, GND, 5V, 5V, GND. J3: GND, TX (GPIO21 U0TXD), RX (GPIO20 U0RXD), GND, IO9, IO8, GND, IO7, IO6, IO5, IO4, GND, IO18, IO19, GND',
                   'Header Block, tables J1 and J3 (positions 1-15 each)', notes='the guide: "All available GPIO pins (except for the SPI bus for flash) are broken out to the pin headers"; the numbering is the DevKitM-1 schematic\'s'),
        board_fact('devkit.rgb_led', 'addressable RGB LED, driven by GPIO8', 'component list "RGB LED"; Header Block J3 pin 6 (IO8, RGB LED)'),
        board_fact('devkit.usb_uart_bridge', 'single USB-UART bridge chip, up to 3 Mbps; the Micro-USB port is the power and communication interface', 'component list "USB-to-UART Bridge", "Micro-USB Port"',
                   notes='which chip pins the bridge uses is not stated in the guide text'),
        board_fact('devkit.boot_button', 'Boot button: download button (hold Boot, press Reset: firmware download mode)', 'component list "Boot Button"', notes='the guide does not name the button\'s GPIO'),
        board_fact('devkit.strapping', 'GPIO2, GPIO8 and GPIO9 are strapping pins', 'Header Block, note [2]'),
        board_fact('module.flash', 'the flash is integrated in the chip\'s package (all MINI-1 variants); ESP32-C3-MINI-1-H4-AZ: SPI0/SPI1 pins for flash connection are not bonded', 'Table 1-1 note 4, p.4; chip list p.4', 'mini'),
        board_fact('module.pins', 'the module breaks out IO0-IO10 (IO8, IO9 included), IO18, IO19, RXD0 (GPIO20), TXD0 (GPIO21), EN; the pins of GPIO11-17 are NC', 'Table 3-1 Pin Definitions, p.11', 'mini'),
    ]

"""
@module board.custom.soc_samd21

THE ATSAMD21G18A's OWN NUMBERS (bob-5, 2026-10-30) - shared by every board spec on that chip (the Arduino Zero, the Feather M0 Express). Cited from Microchip's
SAM D21/DA1 family datasheet (DS40001882L, Revision L, February 2026; read 2026-10-30 - Microchip copyright, cited not stored).
The per-pin drive depends on a FIRMWARE setting (PINCFG.DRVSTR): the datasheet gives maxima only, for normal (DRVSTR=0) and strong (DRVSTR=1) drive.
"""
SOC = 'atsamd21g18a'
DOC = ('Microchip SAM D21/DA1 Family Data Sheet (DS40001882)', 'DS40001882L, Revision L - February 2026, sha256 cd6d39e3e5c2f211... (read 2026-10-30)',
       'https://ww1.microchip.com/downloads/aemDocuments/documents/MCU32/ProductDocuments/DataSheets/SAM-D21-DA1-Family-Data-Sheet-DS40001882.pdf')
#: Table 37-15 (p.916), VDD = 3.0-3.63 V, MAXIMUM values (no typical printed)
DRIVE = {'ioh_max_ma': {'drvstr0': 2.0, 'drvstr1': 7.0}, 'iol_max_ma': {'drvstr0': 2.5, 'drvstr1': 10.0}}

FACTS = [
    ('power.vdd', 3.3, 'V', 'sect 37.4 Table 37-3 General Operating Conditions, p.907', 'VDD min 1.62 (BOD33 disabled), typ 3.3, max 3.63 V', 'ds', 'soc'),
    ('power.absmax', '0..3.8 V; 92 mA into a VDD pin; 130 mA out of a GND pin', '', 'sect 37.3 Table 37-2 Absolute Maximum Ratings, p.907',
     'note 1: "Maximum source current is 46mA and maximum sink current is 65mA per cluster" (the GPIO clusters of Table 7-6)', 'ds', 'soc'),
    ('io.drive_max', 'IOH 2 / 7 mA, IOL 2.5 / 10 mA (DRVSTR 0 / 1)', 'mA', 'sect 37.9.1 Table 37-15 Normal I/O Pins Characteristics, p.916',
     'MAXIMUM output currents at VDD 3.0-3.63 V: source (IOH) 2 mA at DRVSTR=0, 7 mA at DRVSTR=1; sink (IOL) 2.5 mA / 10 mA - no typical values printed', 'ds', 'soc'),
    ('io.levels', 'VIL max 0.3 VDD; VIH min 0.55 VDD; pull 20/40/60 kOhm', '', 'Table 37-15, p.916', 'VDD 2.7-3.63 V; the pulls on all pins except PA24, PA25', 'ds', 'soc'),
]

#: the electrical_json a header pin on this chip carries: the strong-drive maxima (DRVSTR is the firmware's choice; the default-drive figures are said)
ELECTRICAL = {'max_ma': DRIVE['ioh_max_ma']['drvstr1'], 'sink_ma': DRIVE['iol_max_ma']['drvstr1'], 'fact': '%s:io.drive_max' % SOC,
              'kind': 'datasheet maximum at strong drive (DRVSTR=1, a firmware setting); at the default DRVSTR=0: 2 mA source / 2.5 mA sink'}

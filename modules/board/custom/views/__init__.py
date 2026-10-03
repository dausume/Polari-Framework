"""
@module board.custom.views

THE BOARD OBJECT's VIEWS (brd-bo, PCB_FROM_SCRATCH_PLAN §2b "generate out, ingest in, both by hash"): each world's board file
rendered FROM the rows — never kept by hand — and read back by board.custom.ingest:

  kicad    views/kicad.py    a KiCad netlist (`.net`, s-expression, D-pcb-1 written directly): components + footprint refs, nets
                             named from the pins, the connectors with their pin order
  zephyr   views/zephyr.py   a devicetree OVERLAY + Kconfig fragment: pinctrl groups, aliases, chosen console, status = "okay"
                             per peripheral in use — or a REFUSAL (the UNO: no Zephyr target for the ATmega328P)
  esp-idf  views/esp_idf.py  board_pins.h (the C identifiers the template uses) + an sdkconfig fragment (the board-owned lines)
  bare-c   views/bare_c.py   cmod's board_config.h (the same text `pol board gen` writes for a variant) with a provenance banner

Every view names the board and the BOARD SHA (board.custom.board_object.board_sha) it was rendered from; its own sha256 is over
the files it wrote (name + bytes, sorted). The pin names are the BoardPin canonical names in every view (pins named once).
"""
import hashlib

KINDS = ('kicad', 'zephyr', 'esp-idf', 'bare-c')
#: the BoardPin fields each kind CARRIES (what an ingest of it can compare)
CARRIES = {'kicad': ('soc_pin', 'net', 'connector_pin'),
           'zephyr': ('soc_pin', 'net', 'function', 'peripheral', 'signal', 'alias', 'electrical_json'),
           'esp-idf': ('firmware_symbol',), 'bare-c': ('firmware_symbol',)}


class ViewRefused(ValueError):
    pass


def banner(kind, r, sha):
    return ('rendered by `pol board render %s --as %s` (board.custom.views) from THE BOARD OBJECT rows of %s — board sha %s. '
            'Generated: edit the rows (or ingest an edited view), never this file.' % (r['board'], kind, r['board'], sha))


def view_sha(files):
    h = hashlib.sha256()
    for name in sorted(files):
        h.update(name.encode() + b'\0' + files[name].encode() + b'\0')
    return h.hexdigest()


def module(kind):
    from board.custom.views import bare_c, esp_idf, kicad, zephyr
    try:
        return {'kicad': kicad, 'zephyr': zephyr, 'esp-idf': esp_idf, 'bare-c': bare_c}[kind]
    except KeyError:
        raise ViewRefused('no view kind %r — kicad | zephyr | esp-idf | bare-c' % kind)


def render(r, kind):
    """r = board_object.rows_for(...) (or an edited copy) → {'kind', 'files', 'sha256', 'board_sha'}; ViewRefused names why not."""
    from board.custom.board_object import board_sha
    bsha = board_sha(r)
    files = module(kind).render(r, bsha)
    return {'board': r['board'], 'kind': kind, 'files': files, 'sha256': view_sha(files), 'board_sha': bsha}

"""
@module cmod.custom.fsc_prices

fsc-0 (D-fsc-2, his words: "A cited list would be ideal, accounting for the fact you can buy used or locally as well in that."): the READER of cited price OFFERS, one row per
offer: part_class, variant, condition new|used, channel online|local, vendor, price, currency, pack_qty, unit_price, source_title, url, cited_at, confidence page-read|search-snippet,
note. File: modules/board/custom/price_offers/part_price_offers.json ({"offers": [...], "gaps": [...], "method": ...}; a bare list also reads). It is NOT in initialData/ on purpose: that
folder is auto-seeded into a class of the same name at boot and this file is not a row set. Env POLARI_PRICE_OFFERS overrides the path (tests).

`cheapest(part_class, knobs)` -> the cheapest offer the PROFILE accepts (knobs accept_used / accept_local, default true), by unit_price, or None. An absent file or a part class with
no offer is UNDETERMINED: the caller scores it at a stated stand-in (the median cited unit price), never zero. Local offers cite a chain's public list price, never a location
(privacy rule); this reader refuses nothing but also never adds an address.
"""
import json
import os

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'board', 'custom', 'price_offers', 'part_price_offers.json')
#: the board is a part too (bom-cost includes it): board name -> the part class its offers are filed under
BOARD_PART = {'arduino-uno-r3': 'Arduino Uno R3 (board)', 'esp32-c3': 'ESP32-C3 DevKit (board)'}
#: the catalogue says "USB bridge", the offer file "USB connector": the same cable (a bridge chip sits behind the connector) - matched, said
ALIASES = {"usb cable to the host (through the board's usb bridge)": "usb cable to the host (through the board's usb connector)"}
_CACHE = {}


def _norm(s):
    return ' '.join(str(s).lower().split())


def load(path=None):
    path = path or os.environ.get('POLARI_PRICE_OFFERS') or PATH
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return {'offers': [], 'gaps': [], 'path': path, 'present': False, 'cited_at': ''}
    if _CACHE.get('key') != (path, mt):
        data = json.load(open(path, encoding='utf-8'))
        offers = data if isinstance(data, list) else data.get('offers', [])
        ok = [o for o in offers if isinstance(o.get('unit_price'), (int, float)) and o.get('part_class')]
        _CACHE.update(key=(path, mt), val={'offers': ok, 'gaps': [] if isinstance(data, list) else data.get('gaps', []), 'path': path, 'present': True,
                                           'cited_at': '' if isinstance(data, list) else data.get('cited_at', '')})
    return _CACHE['val']


def accepts(offer, knobs):
    k = dict({'accept_used': True, 'accept_local': True}, **(knobs or {}))
    if offer.get('condition') == 'used' and not k['accept_used']:
        return False
    if offer.get('channel') == 'local' and not k['accept_local']:
        return False
    return True


def cheapest(part_class, knobs=None, path=None):
    """-> the cheapest accepted offer for the part class (matched case-insensitively on the declared class string), or None."""
    want = _norm(part_class)
    want = {want, ALIASES.get(want, want)}
    hits = [o for o in load(path)['offers'] if _norm(o['part_class']) in want and accepts(o, knobs)]
    return min(hits, key=lambda o: (o['unit_price'], o.get('condition') != 'new', o.get('channel') != 'online', o.get('url', ''))) if hits else None


def standin_price(path=None, knobs=None):
    """The stand-in for a part class with no cited offer: the MEDIAN cited unit price over the accepted offers (stated). None when there are no offers at all."""
    prices = sorted(o['unit_price'] for o in load(path)['offers'] if accepts(o, knobs))
    if not prices:
        return None
    n = len(prices)
    return prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2.0


def offer_words(o):
    weak = ' (a search snippet - weaker evidence, may be stale)' if o.get('confidence') == 'search-snippet' else ' (page read)'
    return '%s %s/%s offer %.2f %s from %s, cited %s%s%s' % (o['part_class'] + (' [%s]' % o['variant'] if o.get('variant') else ''), o.get('condition', '?'), o.get('channel', '?'),
                                                              o['unit_price'], o.get('currency', 'USD'), o.get('vendor', '?'), o.get('cited_at', '?'), weak, ' ' + o['url'] if o.get('url') else '')


def price_parts(classes, knobs=None, path=None):
    """Price a list of part classes. -> {total, kind, basis, lines[], missing[]}. kind: cited (every class has an accepted offer) or stand-in (some class has none ->
    scored at the median cited unit price, said); no offers file at all -> total None, kind stand-in."""
    st = standin_price(path, knobs)
    total, lines, missing, weak = 0.0, [], [], 0
    for cls in classes:
        o = cheapest(cls, knobs, path)
        if o is None:
            missing.append(cls)
            if st is not None:
                total += st
            lines.append('%s: no accepted offer -> stand-in %s' % (cls, ('%.2f' % st) if st is not None else 'undetermined'))
        else:
            total += o['unit_price']
            weak += o.get('confidence') == 'search-snippet'
            lines.append(offer_words(o))
    if st is None:
        return {'total': None, 'kind': 'stand-in', 'basis': 'no cited price offers are loaded (%s); undetermined' % os.path.basename(PATH), 'lines': lines, 'missing': list(classes)}
    kind = 'cited' if not missing else 'stand-in'
    note = ''
    if missing:
        note = ' %d class(es) have no accepted cited offer and are scored at the median cited unit price %.2f (stand-in): %s.' % (len(missing), st, ', '.join(missing))
    if weak:
        note += ' %d of the offers are search snippets (weaker evidence).' % weak
    k = dict({'accept_used': True, 'accept_local': True}, **(knobs or {}))
    return {'total': round(total, 2), 'kind': kind, 'lines': lines, 'missing': missing,
            'basis': 'cheapest accepted offer per part class (accept_used=%s, accept_local=%s), USD, before tax and shipping:%s | ' % (k['accept_used'], k['accept_local'], note) + ' | '.join(lines)}

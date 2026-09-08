"""
Self-test for mtt-2 research tools: the buildable-instrument catalog
(Dustin's asks + the high-leverage additions), the easiest-first sort,
the accessibility rollup, the honest Brix correlation caveat, and the
research<->manufacturing thermocouple bridge.

Run from polari-framework/ (modules/ on the path):
    python3 -m pspp.research_tools_selftest
"""

import sys

from pspp.research_tools_basis import (
    SEED_RESEARCH_TOOLS, research_tools, tool_dict, validate_tools,
)

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f'  ok: {label}')
    else:
        FAIL += 1
        print(f'  FAIL: {label}')


def test_dustins_asks_present():
    print('[research tools: the requested instruments]')
    names = {t['name'] for t in
             (tool_dict(r) for r in SEED_RESEARCH_TOOLS)}
    check('open-source FTIR present', 'open-source-ftir' in names)
    check('red-cabbage pH detector present',
          'red-cabbage-ph-detector' in names)
    check('sugar/Brix fruit-vegetable test present',
          'brix-refractometer' in names)


def test_easiest_first_and_ftir_honesty():
    print('[research tools: easiest-first + FTIR difficulty honesty]')
    cat = research_tools()
    diffs = [t['difficulty'] for t in cat['tools']]
    order = ['trivial', 'low', 'moderate', 'high']
    check('catalog is sorted easiest-first',
          [order.index(d) for d in diffs]
          == sorted(order.index(d) for d in diffs))
    ftir = next(t for t in cat['tools'] if t['name'] == 'open-source-ftir')
    check('FTIR is honestly the HIGH-difficulty tool',
          ftir['difficulty'] == 'high')
    vis = next(t for t in cat['tools'] if t['name'] == 'visible-spectrometer')
    check('the visible spectrometer is the accessible cousin '
          '(household, low)',
          vis['accessibilityTier'] == 'household'
          and vis['difficulty'] == 'low')
    check('red-cabbage pH is trivial + household',
          next(t for t in cat['tools']
               if t['name'] == 'red-cabbage-ph-detector')['difficulty']
          == 'trivial')


def test_brix_correlation_honesty():
    print('[research tools: Brix correlation, not proof]')
    brix = tool_dict(next(r for r in SEED_RESEARCH_TOOLS
                          if r['name'] == 'brix-refractometer'))
    check('Brix row measures dissolved solids DIRECTLY',
          'dissolved solids' in brix['measures'].lower())
    check('mineral/health is flagged a CORRELATION, not a proof',
          'CORRELATE' in brix['correlationCaveat'].upper()
          and 'proof' in brix['correlationCaveat'].lower())
    ec = tool_dict(next(r for r in SEED_RESEARCH_TOOLS
                        if r['name'] == 'ec-tds-meter'))
    check('EC/TDS is offered as the DIRECT mineral measure',
          'mineral' in ec['measures'].lower())


def test_research_manufacturing_bridge():
    print('[research tools: thermocouple bridges to the furnace ladder]')
    tc = tool_dict(next(r for r in SEED_RESEARCH_TOOLS
                        if r['name'] == 'thermocouple-logger'))
    check('thermocouple logger measures furnace temperature',
          'temperature' in tc['measures'].lower())
    check('its note ties to climbing the manufacturing furnace ladder',
          'ladder' in tc['notes'].lower())


def test_domain_filter_and_validate():
    print('[research tools: domain filter + honesty validation]')
    water = research_tools(domain='water')
    check('domain filter returns only water tools',
          all('water' in t['domains'] for t in water['tools'])
          and len(water['tools']) >= 3)
    check('all tools pass structural validation',
          validate_tools()['ok'])
    check('every tool carries parts + a safety note',
          all(t['parts'] and t['safety']
              for t in research_tools()['tools']))


def main():
    test_dustins_asks_present()
    test_easiest_first_and_ftir_honesty()
    test_brix_correlation_honesty()
    test_research_manufacturing_bridge()
    test_domain_filter_and_validate()
    print(f'\n{PASS} passed, {FAIL} failed')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())

"""
Selftest — chain-1: bio supply-chain rollup (materials + food + carbon),
carbon balance, and dependency check.

Run from polari-framework/:
    python3 -m supplychain.selftest_chain

Covers: the inventory aggregates outputs by kind (materials/food/carbon/
nutrient) across all nodes; carbon balance sums sinks vs sources and
reports net (the demo is a net sink via the algae reactor + tank); the
dependency check passes when every input is met by a flow or external
feedstock, and fails (naming the resource) when a flow is removed;
honest refusals.
"""

from types import SimpleNamespace

from supplychain.chain_analysis import (
    carbon_balance, chain_inventory, dependency_check,
)
from supplychain.chain_seed import (
    SEED_SUPPLY_CHAINS, SEED_SUPPLY_FLOWS, SEED_SUPPLY_NODES,
)

PASS, FAIL = '\033[0;32mPASS\033[0m', '\033[0;31mFAIL\033[0m'
_results = []


def check(label, cond, extra=''):
    _results.append(bool(cond))
    print(f'  [{PASS if cond else FAIL}] {label}'
          f'{("  " + extra) if extra else ""}')


def _rows(seed_list):
    return {i: SimpleNamespace(**r) for i, r in enumerate(seed_list)}


def _mgr(flows=None, chains=None):
    return SimpleNamespace(objectTables={
        'SupplyNode': _rows(SEED_SUPPLY_NODES),
        'SupplyFlow': _rows(flows if flows is not None
                            else SEED_SUPPLY_FLOWS),
        'SupplyChainDefinition': _rows(chains if chains is not None
                                       else SEED_SUPPLY_CHAINS)})


if __name__ == '__main__':
    manager = _mgr()

    print('inventory rollup (materials + food + carbon + nutrient)')
    inv = chain_inventory(manager, 'household-bio-chain')
    check('inventory ok + counts nodes', inv['ok']
          and inv['nodeCount'] == len(SEED_SUPPLY_NODES))
    check('materials include ferrite + KDP + wax + algae biomass',
          {'ferrite-magnet-feedstock', 'kdp-crystal', 'candelilla-wax',
           'algae-biomass'} <= set(inv['materials']))
    check('foods include basil + seaweed + greens + mushrooms',
          {'basil', 'seaweed', 'leafy-greens', 'mushrooms'}
          <= set(inv['foods']))
    check('carbon resources tracked (fixed + cycled + permanent)',
          {'co2-fixed', 'co2-cycled', 'permanent-carbon'}
          <= set(inv['carbon']))
    check('per-module breakdown spans the modules',
          {'aquaponics', 'tanks', 'microalgae', 'biomining',
           'waxsupply', 'garden'} <= set(inv['byModule']))

    print('carbon balance (sinks vs sources)')
    cb = carbon_balance(manager, 'household-bio-chain')
    # 9837 (reactor) + 1800 (tank) + 5.3 (aquaponics) = 11642.3 g/yr sink
    check('carbon sinks summed across the chain',
          abs(cb['carbonSinkPerYear'] - 11642.3) < 1.0,
          extra=str(cb['carbonSinkPerYear']))
    check('net is a carbon SINK', cb['isNetSink']
          and cb['netSequesteredPerYear'] > 0)
    check('per-node carbon contributions listed',
          any(c['node'] == 'algae-reactor-node'
              for c in cb['contributions']))

    print('dependency check')
    dep = dependency_check(manager, 'household-bio-chain')
    check('all inputs satisfied (flows + external feedstock)',
          dep['satisfied'] and not dep['unmetInputs'])
    # Remove the tank->reactor nitrogen flow -> reactor input unmet.
    broken_flows = [f for f in SEED_SUPPLY_FLOWS
                    if f['name'] != 'tank-to-reactor-n']
    dep2 = dependency_check(_mgr(flows=broken_flows),
                            'household-bio-chain')
    check('removing a flow surfaces the unmet input (nitrogen)',
          not dep2['satisfied']
          and any(u['resource'] == 'nitrogen'
                  for u in dep2['unmetInputs']))
    check('unmet limiting factor named',
          dep2['limitingFactor'] and 'unmet' in dep2['limitingFactor'])

    print('honest refusals')
    check('unknown chain refuses',
          not chain_inventory(manager, 'nope').get('ok'))
    empty = SimpleNamespace(objectTables={
        'SupplyNode': _rows(SEED_SUPPLY_NODES), 'SupplyFlow': {},
        'SupplyChainDefinition': _rows([{
            'name': 'empty', 'node_names_json': '[]'}])})
    check('chain with no nodes refuses',
          not chain_inventory(empty, 'empty').get('ok'))

    failed = _results.count(False)
    print(f'\n{len(_results) - failed}/{len(_results)} passed')
    raise SystemExit(1 if failed else 0)

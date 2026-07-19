"""
@module pspp.pspp_views

Pure view-builders behind the PSPP HTTP surface (pspp_api) — every
chart the frontend draws is GENERATED from DigitizedDataset /
ReactionRule / ReactionWindow rows here, so editing a row via the
auto-CRUDE API changes the picture (invariant I6 extended to pixels).
Live rows win; the book-transcription seeds are the fallback so the
views work before first boot-seed.
"""

import json

from pspp.dataset_interpolation import read_dataset
from pspp.digitized_datasets import dataset_dict, dataset_index
from pspp.datasets_seed import SEED_DIGITIZED_DATASETS
from pspp.reaction_network import (
    REACTION_STAGES, SEED_CHEMICAL_SPECIES, SEED_REACTION_RULES,
)
from pspp.reaction_windows import (
    SEED_REACTION_WINDOWS, window_dict,
)
from pspp.threshold_windows import (
    SEED_THRESHOLD_WINDOWS, banded_window_dict,
    grade_composition_merged,
)
from pspp.composition_math import oxide_ratios, ratios_from_moles
from pspp.state_resolution import material_states


def _rows(manager, table):
    rows = (getattr(manager, 'objectTables', None) or {}).get(table, {})
    return list(rows.values()) if isinstance(rows, dict) else list(rows)


def _datasets(manager):
    live = dataset_index(manager) if manager is not None else {}
    if live:
        return live
    return {d['name']: d
            for d in (dataset_dict(s) for s in SEED_DIGITIZED_DATASETS)}


def dataset_catalog(manager):
    """The dataset browser payload — names, citations, variables,
    status, and honesty metadata (never the raw points; the curve
    endpoint serves those with interpolation semantics attached)."""
    out = []
    for d in sorted(_datasets(manager).values(),
                    key=lambda x: x['name']):
        out.append({
            'name': d['name'],
            'source': d['sourceReference'],
            'status': d['status'],
            'independentVariables': d['independentVariables'],
            'dependentVariables': d['dependentVariables'],
            'units': d['units'],
            'interpolationPolicy': d['interpolationPolicy'],
            'extrapolationPolicy': d['extrapolationPolicy'],
            'validityDomain': d['validityDomain'],
            'digitizationMethod': d['digitizationMethod'],
            'digitizationError': d['digitizationError'],
            'pointCount': len(d['points']),
            'qualitativeShape': d['qualitativeShape'],
        })
    return {'ok': True, 'datasets': out}


def _series_labels(dataset):
    labels = sorted({str(p['series']) for p in dataset['points']
                     if 'series' in p})
    return labels or [None]


def dataset_curve(manager, name, samples=60):
    """One dataset as chart-ready series: the SOURCE points (drawn as
    markers — these are the book's own values) plus, when the policy
    interpolates, a sampled curve with min/max bands. Discrete
    datasets return points only, honestly marked."""
    dataset = _datasets(manager).get(name)
    if dataset is None:
        return {'ok': False,
                'refusal': f'unknown dataset {name!r}',
                'suggestion': 'GET /api/pspp/datasets for the catalog'}
    if dataset['status'] != 'ready' or not dataset['points']:
        return {'ok': False,
                'refusal': f'dataset {name!r} is '
                           f"{dataset['status']!r} with "
                           f"{len(dataset['points'])} points",
                'qualitativeShape': dataset['qualitativeShape'],
                'suggestion': 'provisional datasets render their '
                              'qualitative shape + validity domain, '
                              'never invented points'}

    numeric = [v for v in dataset['independentVariables']
               if any(isinstance(p.get(v), (int, float))
                      for p in dataset['points'])]
    xVar = numeric[0] if numeric else None
    series = []
    for label in _series_labels(dataset):
        points = [p for p in dataset['points']
                  if label is None or str(p.get('series')) == label]
        points = sorted(points, key=lambda p: p.get(xVar, 0))
        entry = {
            'series': label or dataset['name'],
            'sourcePoints': points,
            'sampled': [],
        }
        interpolable = (dataset['interpolationPolicy'] != 'none'
                        and xVar is not None and len(points) >= 2)
        if interpolable:
            lo = points[0][xVar]
            hi = points[-1][xVar]
            for i in range(samples + 1):
                x = lo + (hi - lo) * i / samples
                query = {xVar: x}
                if label is not None:
                    query['series'] = label
                result = read_dataset(dataset, query)
                if result.get('ok'):
                    entry['sampled'].append({
                        'x': x,
                        'values': result['values'],
                        'band': result['band'],
                        'method': result['evidence']['method'],
                    })
        series.append(entry)
    return {
        'ok': True,
        'name': dataset['name'],
        'source': dataset['sourceReference'],
        'xVariable': xVar,
        'dependentVariables': dataset['dependentVariables'],
        'units': dataset['units'],
        'interpolationPolicy': dataset['interpolationPolicy'],
        'validityDomain': dataset['validityDomain'],
        'digitizationMethod': dataset['digitizationMethod'],
        'digitizationError': dataset['digitizationError'],
        'series': series,
    }


def _seed_or_rows(manager, table, seeds):
    rows = _rows(manager, table)
    if rows:
        return [{k: getattr(r, k) for k in vars(r)
                 if not k.startswith('_')} if not isinstance(r, dict)
                else r for r in rows]
    return seeds


def network_graph(manager):
    """The reaction network as a drawable graph: species + rule nodes,
    reactant/product edges, laid out by REACTION_STAGES columns.
    Every rule node carries its evidence payload (hypothesis status,
    site constraint, source) so the frontend can style competing
    hypotheses and transport selection distinctly."""
    def get(row, key, default=''):
        return row.get(key, default) if isinstance(row, dict) \
            else getattr(row, key, default)

    species = _seed_or_rows(manager, 'ChemicalSpecies',
                            SEED_CHEMICAL_SPECIES)
    rules = _seed_or_rows(manager, 'ReactionRule', SEED_REACTION_RULES)
    nodes, edges = [], []
    for s in species:
        nodes.append({
            'id': get(s, 'name'), 'kind': 'species',
            'label': get(s, 'display_name') or get(s, 'name'),
            'formula': get(s, 'formula'),
            'speciesKind': get(s, 'species_kind', 'molecule'),
            'qn': get(s, 'qn', -1),
            'notes': get(s, 'notes'),
        })
    for r in rules:
        rid = get(r, 'name')
        stage = get(r, 'stage')
        nodes.append({
            'id': rid, 'kind': 'rule',
            'label': get(r, 'display_name') or rid,
            'stage': stage,
            'stageIndex': (REACTION_STAGES.index(stage)
                           if stage in REACTION_STAGES else -1),
            'hypothesisStatus': get(r, 'hypothesis_status'),
            'siteConstraint': get(r, 'site_constraint'),
            'kineticsStatus': get(r, 'kinetics_status', 'none'),
            'topologyChange': get(r, 'topology_change'),
            'source': get(r, 'source_reference'),
            'competingWith': json.loads(
                get(r, 'competing_with_json', '[]') or '[]'),
            'family': get(r, 'material_family', 'general'),
        })
        for reactant in json.loads(get(r, 'reactants_json', '[]')
                                   or '[]'):
            edges.append({'from': reactant, 'to': rid,
                          'role': 'reactant'})
        for product in json.loads(get(r, 'products_json', '[]')
                                  or '[]'):
            edges.append({'from': rid, 'to': product,
                          'role': 'product'})
    return {'ok': True, 'stages': list(REACTION_STAGES),
            'nodes': nodes, 'edges': edges}


def grade_payload(manager, composition, basis='mass', family=''):
    """Composition → derived ratios → graded windows, chart-ready.
    The unjudged list and every refusal ride along (they render AS
    refusals — never silently absent)."""
    if not isinstance(composition, dict) or not composition:
        return {'ok': False,
                'refusal': 'composition must be a non-empty '
                           '{oxide: amount} dict',
                'suggestion': "e.g. {'SiO2': 55, 'Al2O3': 25, "
                              "'Na2O': 10, 'H2O': 10}"}
    derive = oxide_ratios if basis == 'mass' else ratios_from_moles
    ratios = derive({k: float(v) for k, v in composition.items()})
    if not ratios.get('ok'):
        return ratios
    windows = _seed_or_rows(manager, 'ReactionWindow',
                            SEED_REACTION_WINDOWS)
    banded = _seed_or_rows(manager, 'ThresholdReactionWindow',
                           SEED_THRESHOLD_WINDOWS)
    windowDicts = [window_dict(w) for w in windows]
    # Condition-gate windows open/close PATHWAYS (the /pathways
    # surface) — they never grade a composition.
    bandedDicts = [w for w in (banded_window_dict(x) for x in banded)
                   if w['windowRole'] == 'quality']
    families = sorted({w['materialFamily']
                       for w in windowDicts + bandedDicts})
    graded = grade_composition_merged(
        windows, banded, ratios['ratios'], family) if family else {
        'ok': False,
        'refusal': 'no material_family selected',
        'suggestion': f'pick one of {families}'}
    return {
        'ok': True,
        'basis': basis,
        'ratios': ratios['ratios'],
        'absentDenominators': ratios['absentDenominators'],
        'families': families,
        'windows': [w for w in windowDicts
                    if not family or w['materialFamily'] == family],
        'bandedWindows': [w for w in bandedDicts
                          if not family
                          or w['materialFamily'] == family],
        'grading': graded,
    }


def state_dag(manager, material_name):
    """One material's state DAG, chart-ready (nodes + parent edges,
    implicit canonical included)."""
    states = material_states(manager, material_name)
    edges = [{'from': parent, 'to': s['stateKey']}
             for s in states for parent in s['parents']]
    return {'ok': True, 'material': material_name,
            'states': states, 'edges': edges}

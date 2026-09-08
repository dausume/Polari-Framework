"""@module scoring.objects.policy_votes._shared — what the policy_votes row classes share (constants, seeds, helpers); split from policy_votes_basis.py (sap-2c)."""
import json

VOTE_KINDS = ('yea', 'nay', 'abstain')
def _rows(manager, class_name):
    table = (manager.objectTables or {}).get(class_name, {})
    return list(table.values()) if isinstance(table, dict) else list(table)
def _names(manager, class_name):
    return {getattr(r, 'name', '') for r in _rows(manager, class_name)}
def _slug(text):
    return str(text).strip().lower().replace(' ', '-')
SEED_POLICY_VOTES = [
    {
        'name': 'vote-pol-rivera@policy-fair-wage-act',
        'politician_name': 'pol-rivera',
        'policy_name': 'policy-fair-wage-act',
        'vote': 'yea', 'vote_date': '2024-04-15',
        'chamber': 'assembly',
        'provenance_id': 'scr-6 demo roll call',
    },
    {
        'name': 'vote-pol-rivera@policy-labor-standards-2020',
        'politician_name': 'pol-rivera',
        'policy_name': 'policy-labor-standards-2020',
        'vote': 'yea', 'vote_date': '2020-06-15',
        'chamber': 'assembly',
        'provenance_id': 'scr-6 demo roll call',
    },
    {
        'name': 'vote-pol-stone@policy-fair-wage-act',
        'politician_name': 'pol-stone',
        'policy_name': 'policy-fair-wage-act',
        'vote': 'nay', 'vote_date': '2024-04-15',
        'chamber': 'assembly',
        'provenance_id': 'scr-6 demo roll call',
    },
    {
        'name': 'vote-pol-stone@policy-labor-standards-2020',
        'politician_name': 'pol-stone',
        'policy_name': 'policy-labor-standards-2020',
        'vote': 'abstain', 'vote_date': '2020-06-15',
        'chamber': 'assembly',
        'provenance_id': 'scr-6 demo roll call — abstention is a '
                         'participation gap, surfaced not scored',
    },
]
SEED_POLITICIAN_SUBJECTS = [
    {
        'name': 'pol-rivera', 'display_name': 'Rep. Rivera (demo)',
        'kind': 'politician',
        'description': 'Demo politician — voted yea on both labor '
                       'policies.',
    },
    {
        'name': 'pol-stone', 'display_name': 'Rep. Stone (demo)',
        'kind': 'politician',
        'description': 'Demo politician — nay on the Fair Wage Act, '
                       'abstained on Labor Standards.',
    },
]
SEED_COHORT_GROUPS = [
    {
        'name': 'demo-assembly-labor-committee',
        'display_name': 'Assembly Labor Committee (demo)',
        'group_type': 'political',
        'member_subject_names_json': json.dumps(
            ['pol-rivera', 'pol-stone']),
        'description': 'Demo politician cohort — the split votes '
                       'exercise the divisive cohort read.',
    },
]

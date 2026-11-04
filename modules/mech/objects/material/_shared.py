"""@module mech.objects.material._shared — what the material row classes share (vocabularies); mxc-1, MECH_FREECAD_INTERCHANGE_PLAN section 3.3 / 9.1 / D-mxc-9."""

#: The realization ladder is composition's (magnetics asserts the same
#: tuple) — one vocabulary, not a copy.
from composition.custom.realization import REALIZATION_LEVELS  # noqa: F401

#: Registry `cls`, widened for the rows the drawer plan needs (wood) and
#: the ones a later catalogue will (ceramic, composite). The collab
#: registry says 'plastic' where this vocabulary says 'polymer'
#: (CLASS_ALIASES maps it on import); 'fibre', 'coating', 'additive'
#: are the registry's own and stay.
MATERIAL_CLASSES = ('polymer', 'elastomer', 'metal', 'wood', 'ceramic',
                    'composite', 'fibre', 'coating', 'additive')
CLASS_ALIASES = {'plastic': 'polymer'}

#: Plan section 3.3 and the registry agree: polari_acceptable, not a
#: bare 'acceptable'.
STATUSES = ('polari_preferred', 'polari_acceptable', 'legacy_harmful')

#: IARC monograph groups as the registry writes them on a feedstock;
#: 'check' = the registry itself says confirm; 'none' = not evaluated.
#: Ordered worst-first so worst_feedstock_iarc is min() by index.
IARC_GROUPS = ('1', '2A', '2B', 'check', '3', 'none')

#: Registry judgement confidence.
CONFIDENCES = ('good', 'check')


def worst_iarc(feedstocks):
    """Worst group across a feedstock list ('none' when empty)."""
    order = {g: i for i, g in enumerate(IARC_GROUPS)}
    groups = [f.get('iarc', 'none') for f in feedstocks or ()]
    return min(groups, key=lambda g: order.get(g, 99), default='none')

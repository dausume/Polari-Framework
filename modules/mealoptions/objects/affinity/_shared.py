"""@module mealoptions.objects.affinity._shared — what the affinity row classes share (constants, seeds, helpers); split from affinity_basis.py (sap-2c)."""

DEFAULT_CONTEXT = 'general-western'
def _base(name, display, desc=''):
    return {'name': name, 'display_name': display,
            'description': desc, 'is_prior': True,
            'provenance_id': 'nmp-11'}
SEED_DISH_BASES = [
    _base('omelet', 'Omelet', 'eggs folded around fillings'),
    _base('salad', 'Salad', 'raw-forward bowl, dressed'),
    _base('pasta', 'Pasta', 'noodles + sauce + toppings'),
    _base('stir-fry', 'Stir-fry', 'high-heat pan toss over a starch'),
    _base('soup', 'Soup', 'simmered in broth'),
    _base('bowl', 'Grain bowl', 'starch base + protein + vegetables'),
    _base('sandwich', 'Sandwich', 'fillings between bread'),
]
def _role(name, display):
    return {'name': name, 'display_name': display, 'is_prior': True,
            'provenance_id': 'nmp-11'}
SEED_INGREDIENT_ROLES = [
    _role('diced-protein', 'Diced protein'),
    _role('leafy-green', 'Leafy green'),
    _role('vegetable', 'Vegetable'),
    _role('aromatic', 'Aromatic'),
    _role('starch-base', 'Starch base'),
    _role('dressing-oil', 'Dressing / oil'),
    _role('fruit-topping', 'Fruit topping'),
    _role('crunch', 'Crunch'),
]
def _fr(food, role):
    return {'name': f'{food}--{role}', 'food_name': food,
            'role_name': role, 'is_prior': True,
            'provenance_id': 'nmp-11'}
SEED_FOOD_ROLES = [
    _fr('chicken-breast-raw', 'diced-protein'),
    _fr('tofu-firm', 'diced-protein'),
    _fr('salmon-atlantic-raw', 'diced-protein'),
    _fr('egg-whole-raw', 'diced-protein'),
    _fr('spinach-raw', 'leafy-green'),
    _fr('kale-raw', 'leafy-green'),
    _fr('lettuce-romaine-raw', 'leafy-green'),
    _fr('broccoli-raw', 'vegetable'),
    _fr('bell-pepper-red-raw', 'vegetable'),
    _fr('carrot-raw', 'vegetable'),
    _fr('mushroom-white-raw', 'vegetable'),
    _fr('tomato-raw', 'vegetable'),
    _fr('onion-raw', 'aromatic'),
    _fr('garlic-raw', 'aromatic'),
    _fr('rice-white-raw', 'starch-base'),
    _fr('rice-brown-raw', 'starch-base'),
    _fr('pasta-dry', 'starch-base'),
    _fr('quinoa-raw', 'starch-base'),
    _fr('olive-oil', 'dressing-oil'),
    _fr('banana-raw', 'fruit-topping'),
    _fr('strawberries-raw', 'fruit-topping'),
    _fr('blueberries-raw', 'fruit-topping'),
    _fr('apple-raw', 'fruit-topping'),
    _fr('almonds-raw', 'crunch'),
    _fr('walnuts-raw', 'crunch'),
]
def _aff(subject, base, weight, context=DEFAULT_CONTEXT,
         source='curated norm', notes=''):
    return {'name': f'{subject}--{base}--{context}',
            'subject': subject, 'dish_base': base,
            'context': context, 'weight': weight, 'source': source,
            'is_prior': True, 'provenance_id': 'nmp-11',
            'notes': notes}
SEED_INGREDIENT_AFFINITIES = [
    # role x base norms (general-western)
    _aff('diced-protein', 'omelet', 0.8),
    _aff('diced-protein', 'salad', 0.9),
    _aff('diced-protein', 'pasta', 0.7),
    _aff('diced-protein', 'stir-fry', 0.95),
    _aff('diced-protein', 'soup', 0.8),
    _aff('diced-protein', 'bowl', 0.95),
    _aff('diced-protein', 'sandwich', 0.85),
    _aff('leafy-green', 'salad', 1.0),
    _aff('leafy-green', 'omelet', 0.7),
    _aff('leafy-green', 'soup', 0.6),
    _aff('leafy-green', 'bowl', 0.8),
    _aff('leafy-green', 'pasta', 0.5),
    _aff('vegetable', 'stir-fry', 0.95),
    _aff('vegetable', 'soup', 0.9),
    _aff('vegetable', 'bowl', 0.85),
    _aff('vegetable', 'salad', 0.8),
    _aff('vegetable', 'omelet', 0.6),
    _aff('vegetable', 'pasta', 0.6),
    _aff('aromatic', 'stir-fry', 0.9),
    _aff('aromatic', 'soup', 0.95),
    _aff('aromatic', 'pasta', 0.85),
    _aff('aromatic', 'omelet', 0.6),
    _aff('starch-base', 'bowl', 1.0),
    _aff('starch-base', 'stir-fry', 0.8),
    _aff('starch-base', 'soup', 0.5),
    _aff('dressing-oil', 'salad', 1.0),
    _aff('dressing-oil', 'pasta', 0.8),
    _aff('fruit-topping', 'salad', 0.6,
         source='curated norm; shared-compound pairings per Ahn '
                'et al. 2011 flavor network (aggregate data)'),
    _aff('fruit-topping', 'omelet', 0.2),
    _aff('fruit-topping', 'pasta', 0.05,
         notes='low = UNUSUAL, never forbidden — banana-on-pasta '
               'is allowed with a gentle note'),
    _aff('crunch', 'salad', 0.9),
    _aff('crunch', 'bowl', 0.7),
    # direct food rows (outrank roles)
    _aff('tomato-raw', 'pasta', 0.95,
         source='curated norm; Ahn 2011 tomato-pasta co-occurrence'),
    _aff('egg-whole-raw', 'omelet', 1.0),
    # context examples (the knob is the person's stated frame)
    _aff('rice-white-raw', 'bowl', 1.0, context='japanese'),
    _aff('tofu-firm', 'soup', 0.95, context='japanese'),
    _aff('black-beans-dry', 'bowl', 0.95, context='mexican'),
]

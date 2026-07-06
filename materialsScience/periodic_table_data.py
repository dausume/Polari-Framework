"""
@module materialsScience.periodic_table_data

The raw periodic-table dataset the seeds are generated from: one
compact tuple per element (Z, symbol, name, group, period, category
code, atomic mass) plus a common-ions table (explicit entries + family
defaults). Data only — no Polari imports — so selftests can validate it
standalone and the seed stays a thin generator.

Category codes → categories:
  ak alkali-metal      ae alkaline-earth     tm transition-metal
  pt post-transition   md metalloid          nm reactive-nonmetal
  hl halogen           ng noble-gas          la lanthanide
  ac actinide          uk unknown-properties
"""

CATEGORY_BY_CODE = {
    'ak': 'alkali-metal', 'ae': 'alkaline-earth', 'tm': 'transition-metal',
    'pt': 'post-transition', 'md': 'metalloid', 'nm': 'reactive-nonmetal',
    'hl': 'halogen', 'ng': 'noble-gas', 'la': 'lanthanide',
    'ac': 'actinide', 'uk': 'unknown-properties',
}

# (Z, symbol, name, group, period, category code, atomic mass)
ELEMENTS = [
    (1, 'H', 'Hydrogen', 1, 1, 'nm', 1.008),
    (2, 'He', 'Helium', 18, 1, 'ng', 4.0026),
    (3, 'Li', 'Lithium', 1, 2, 'ak', 6.94),
    (4, 'Be', 'Beryllium', 2, 2, 'ae', 9.0122),
    (5, 'B', 'Boron', 13, 2, 'md', 10.81),
    (6, 'C', 'Carbon', 14, 2, 'nm', 12.011),
    (7, 'N', 'Nitrogen', 15, 2, 'nm', 14.007),
    (8, 'O', 'Oxygen', 16, 2, 'nm', 15.999),
    (9, 'F', 'Fluorine', 17, 2, 'hl', 18.998),
    (10, 'Ne', 'Neon', 18, 2, 'ng', 20.180),
    (11, 'Na', 'Sodium', 1, 3, 'ak', 22.990),
    (12, 'Mg', 'Magnesium', 2, 3, 'ae', 24.305),
    (13, 'Al', 'Aluminium', 13, 3, 'pt', 26.982),
    (14, 'Si', 'Silicon', 14, 3, 'md', 28.085),
    (15, 'P', 'Phosphorus', 15, 3, 'nm', 30.974),
    (16, 'S', 'Sulfur', 16, 3, 'nm', 32.06),
    (17, 'Cl', 'Chlorine', 17, 3, 'hl', 35.45),
    (18, 'Ar', 'Argon', 18, 3, 'ng', 39.948),
    (19, 'K', 'Potassium', 1, 4, 'ak', 39.098),
    (20, 'Ca', 'Calcium', 2, 4, 'ae', 40.078),
    (21, 'Sc', 'Scandium', 3, 4, 'tm', 44.956),
    (22, 'Ti', 'Titanium', 4, 4, 'tm', 47.867),
    (23, 'V', 'Vanadium', 5, 4, 'tm', 50.942),
    (24, 'Cr', 'Chromium', 6, 4, 'tm', 51.996),
    (25, 'Mn', 'Manganese', 7, 4, 'tm', 54.938),
    (26, 'Fe', 'Iron', 8, 4, 'tm', 55.845),
    (27, 'Co', 'Cobalt', 9, 4, 'tm', 58.933),
    (28, 'Ni', 'Nickel', 10, 4, 'tm', 58.693),
    (29, 'Cu', 'Copper', 11, 4, 'tm', 63.546),
    (30, 'Zn', 'Zinc', 12, 4, 'tm', 65.38),
    (31, 'Ga', 'Gallium', 13, 4, 'pt', 69.723),
    (32, 'Ge', 'Germanium', 14, 4, 'md', 72.630),
    (33, 'As', 'Arsenic', 15, 4, 'md', 74.922),
    (34, 'Se', 'Selenium', 16, 4, 'nm', 78.971),
    (35, 'Br', 'Bromine', 17, 4, 'hl', 79.904),
    (36, 'Kr', 'Krypton', 18, 4, 'ng', 83.798),
    (37, 'Rb', 'Rubidium', 1, 5, 'ak', 85.468),
    (38, 'Sr', 'Strontium', 2, 5, 'ae', 87.62),
    (39, 'Y', 'Yttrium', 3, 5, 'tm', 88.906),
    (40, 'Zr', 'Zirconium', 4, 5, 'tm', 91.224),
    (41, 'Nb', 'Niobium', 5, 5, 'tm', 92.906),
    (42, 'Mo', 'Molybdenum', 6, 5, 'tm', 95.95),
    (43, 'Tc', 'Technetium', 7, 5, 'tm', 98.0),
    (44, 'Ru', 'Ruthenium', 8, 5, 'tm', 101.07),
    (45, 'Rh', 'Rhodium', 9, 5, 'tm', 102.91),
    (46, 'Pd', 'Palladium', 10, 5, 'tm', 106.42),
    (47, 'Ag', 'Silver', 11, 5, 'tm', 107.87),
    (48, 'Cd', 'Cadmium', 12, 5, 'tm', 112.41),
    (49, 'In', 'Indium', 13, 5, 'pt', 114.82),
    (50, 'Sn', 'Tin', 14, 5, 'pt', 118.71),
    (51, 'Sb', 'Antimony', 15, 5, 'md', 121.76),
    (52, 'Te', 'Tellurium', 16, 5, 'md', 127.60),
    (53, 'I', 'Iodine', 17, 5, 'hl', 126.90),
    (54, 'Xe', 'Xenon', 18, 5, 'ng', 131.29),
    (55, 'Cs', 'Caesium', 1, 6, 'ak', 132.91),
    (56, 'Ba', 'Barium', 2, 6, 'ae', 137.33),
    (57, 'La', 'Lanthanum', 3, 6, 'la', 138.91),
    (58, 'Ce', 'Cerium', 3, 6, 'la', 140.12),
    (59, 'Pr', 'Praseodymium', 3, 6, 'la', 140.91),
    (60, 'Nd', 'Neodymium', 3, 6, 'la', 144.24),
    (61, 'Pm', 'Promethium', 3, 6, 'la', 145.0),
    (62, 'Sm', 'Samarium', 3, 6, 'la', 150.36),
    (63, 'Eu', 'Europium', 3, 6, 'la', 151.96),
    (64, 'Gd', 'Gadolinium', 3, 6, 'la', 157.25),
    (65, 'Tb', 'Terbium', 3, 6, 'la', 158.93),
    (66, 'Dy', 'Dysprosium', 3, 6, 'la', 162.50),
    (67, 'Ho', 'Holmium', 3, 6, 'la', 164.93),
    (68, 'Er', 'Erbium', 3, 6, 'la', 167.26),
    (69, 'Tm', 'Thulium', 3, 6, 'la', 168.93),
    (70, 'Yb', 'Ytterbium', 3, 6, 'la', 173.05),
    (71, 'Lu', 'Lutetium', 3, 6, 'la', 174.97),
    (72, 'Hf', 'Hafnium', 4, 6, 'tm', 178.49),
    (73, 'Ta', 'Tantalum', 5, 6, 'tm', 180.95),
    (74, 'W', 'Tungsten', 6, 6, 'tm', 183.84),
    (75, 'Re', 'Rhenium', 7, 6, 'tm', 186.21),
    (76, 'Os', 'Osmium', 8, 6, 'tm', 190.23),
    (77, 'Ir', 'Iridium', 9, 6, 'tm', 192.22),
    (78, 'Pt', 'Platinum', 10, 6, 'tm', 195.08),
    (79, 'Au', 'Gold', 11, 6, 'tm', 196.97),
    (80, 'Hg', 'Mercury', 12, 6, 'tm', 200.59),
    (81, 'Tl', 'Thallium', 13, 6, 'pt', 204.38),
    (82, 'Pb', 'Lead', 14, 6, 'pt', 207.2),
    (83, 'Bi', 'Bismuth', 15, 6, 'pt', 208.98),
    (84, 'Po', 'Polonium', 16, 6, 'pt', 209.0),
    (85, 'At', 'Astatine', 17, 6, 'hl', 210.0),
    (86, 'Rn', 'Radon', 18, 6, 'ng', 222.0),
    (87, 'Fr', 'Francium', 1, 7, 'ak', 223.0),
    (88, 'Ra', 'Radium', 2, 7, 'ae', 226.0),
    (89, 'Ac', 'Actinium', 3, 7, 'ac', 227.0),
    (90, 'Th', 'Thorium', 3, 7, 'ac', 232.04),
    (91, 'Pa', 'Protactinium', 3, 7, 'ac', 231.04),
    (92, 'U', 'Uranium', 3, 7, 'ac', 238.03),
    (93, 'Np', 'Neptunium', 3, 7, 'ac', 237.0),
    (94, 'Pu', 'Plutonium', 3, 7, 'ac', 244.0),
    (95, 'Am', 'Americium', 3, 7, 'ac', 243.0),
    (96, 'Cm', 'Curium', 3, 7, 'ac', 247.0),
    (97, 'Bk', 'Berkelium', 3, 7, 'ac', 247.0),
    (98, 'Cf', 'Californium', 3, 7, 'ac', 251.0),
    (99, 'Es', 'Einsteinium', 3, 7, 'ac', 252.0),
    (100, 'Fm', 'Fermium', 3, 7, 'ac', 257.0),
    (101, 'Md', 'Mendelevium', 3, 7, 'ac', 258.0),
    (102, 'No', 'Nobelium', 3, 7, 'ac', 259.0),
    (103, 'Lr', 'Lawrencium', 3, 7, 'ac', 262.0),
    (104, 'Rf', 'Rutherfordium', 4, 7, 'tm', 267.0),
    (105, 'Db', 'Dubnium', 5, 7, 'tm', 268.0),
    (106, 'Sg', 'Seaborgium', 6, 7, 'tm', 269.0),
    (107, 'Bh', 'Bohrium', 7, 7, 'tm', 270.0),
    (108, 'Hs', 'Hassium', 8, 7, 'tm', 269.0),
    (109, 'Mt', 'Meitnerium', 9, 7, 'uk', 278.0),
    (110, 'Ds', 'Darmstadtium', 10, 7, 'uk', 281.0),
    (111, 'Rg', 'Roentgenium', 11, 7, 'uk', 282.0),
    (112, 'Cn', 'Copernicium', 12, 7, 'tm', 285.0),
    (113, 'Nh', 'Nihonium', 13, 7, 'uk', 286.0),
    (114, 'Fl', 'Flerovium', 14, 7, 'pt', 289.0),
    (115, 'Mc', 'Moscovium', 15, 7, 'uk', 290.0),
    (116, 'Lv', 'Livermorium', 16, 7, 'pt', 293.0),
    (117, 'Ts', 'Tennessine', 17, 7, 'uk', 294.0),
    (118, 'Og', 'Oganesson', 18, 7, 'uk', 294.0),
]

# Explicit common ions by symbol; families without an entry fall back to
# DEFAULT_IONS_BY_CODE (lanthanides/actinides → the 3+ state; noble
# gases / unknowns → none).
COMMON_IONS = {
    'H': ['H+', 'H-'], 'Li': ['Li+'], 'Be': ['Be2+'],
    'C': ['C4-'], 'N': ['N3-'], 'O': ['O2-'], 'F': ['F-'],
    'Na': ['Na+'], 'Mg': ['Mg2+'], 'Al': ['Al3+'], 'P': ['P3-'],
    'S': ['S2-'], 'Cl': ['Cl-'], 'K': ['K+'], 'Ca': ['Ca2+'],
    'Sc': ['Sc3+'], 'Ti': ['Ti2+', 'Ti3+', 'Ti4+'],
    'V': ['V2+', 'V3+', 'V4+', 'V5+'], 'Cr': ['Cr2+', 'Cr3+', 'Cr6+'],
    'Mn': ['Mn2+', 'Mn3+', 'Mn4+', 'Mn7+'], 'Fe': ['Fe2+', 'Fe3+'],
    'Co': ['Co2+', 'Co3+'], 'Ni': ['Ni2+'], 'Cu': ['Cu+', 'Cu2+'],
    'Zn': ['Zn2+'], 'Ga': ['Ga3+'], 'Ge': ['Ge2+', 'Ge4+'],
    'As': ['As3-', 'As3+', 'As5+'], 'Se': ['Se2-'], 'Br': ['Br-'],
    'Rb': ['Rb+'], 'Sr': ['Sr2+'], 'Y': ['Y3+'], 'Zr': ['Zr4+'],
    'Nb': ['Nb5+'], 'Mo': ['Mo4+', 'Mo6+'], 'Tc': ['Tc7+'],
    'Ru': ['Ru3+', 'Ru4+'], 'Rh': ['Rh3+'], 'Pd': ['Pd2+'],
    'Ag': ['Ag+'], 'Cd': ['Cd2+'], 'In': ['In3+'],
    'Sn': ['Sn2+', 'Sn4+'], 'Sb': ['Sb3+', 'Sb5+'], 'Te': ['Te2-'],
    'I': ['I-'], 'Cs': ['Cs+'], 'Ba': ['Ba2+'],
    'Ce': ['Ce3+', 'Ce4+'], 'Eu': ['Eu2+', 'Eu3+'],
    'Yb': ['Yb2+', 'Yb3+'],
    'Hf': ['Hf4+'], 'Ta': ['Ta5+'], 'W': ['W6+'], 'Re': ['Re7+'],
    'Os': ['Os4+'], 'Ir': ['Ir3+', 'Ir4+'], 'Pt': ['Pt2+', 'Pt4+'],
    'Au': ['Au+', 'Au3+'], 'Hg': ['Hg+', 'Hg2+'],
    'Tl': ['Tl+', 'Tl3+'], 'Pb': ['Pb2+', 'Pb4+'], 'Bi': ['Bi3+'],
    'Po': ['Po2+'], 'At': ['At-'], 'Fr': ['Fr+'], 'Ra': ['Ra2+'],
    'Th': ['Th4+'], 'Pa': ['Pa5+'], 'U': ['U3+', 'U4+', 'U6+'],
    'Np': ['Np5+'], 'Pu': ['Pu3+', 'Pu4+'],
}

DEFAULT_IONS_BY_CODE = {
    'la': lambda sym: [f'{sym}3+'],
    'ac': lambda sym: [f'{sym}3+'],
}


def common_ions_for(symbol: str, code: str):
    if symbol in COMMON_IONS:
        return COMMON_IONS[symbol]
    default = DEFAULT_IONS_BY_CODE.get(code)
    return default(symbol) if default else []


def display_position(z: int, group: int, period: int, code: str):
    """(row, col) on the standard 18-column layout — f-block elements
    drop to their own rows (8.5 / 9.5) at columns 3-17."""
    if code == 'la':
        return 8.5, 3.0 + (z - 57)
    if code == 'ac':
        return 9.5, 3.0 + (z - 89)
    return float(period), float(group)

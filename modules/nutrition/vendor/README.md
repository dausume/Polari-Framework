# nutrition/vendor — license-clean vendored datasets (nmp-0)

Every file here is versioned, cited, license-verified data adopted
per AI-Notes/plans/NUTRITION_MEAL_PLANNING_PLAN.md §nmp-0. Values
are VERBATIM from the sources; only container formats changed
(caret-delimited text / xlsx / HTML tables → CSV). Loaders:
`nutrition/vendor_data.py`. Retrieved **2026-08-20**.

CSV (not JSON) is deliberate: the repo `.gitignore` blanket-ignores
`*.json` — a JSON data file here would silently vanish from git.

| file | source | license | sha256 |
|---|---|---|---|
| `usda_retention_factors_r6.csv` | USDA Table of Nutrient Retention Factors, Release 6 (2007) — ars.usda.gov `/ARSUserFiles/80400535/Data/retn/retn06.txt` (7,018 rows, converted from caret-delimited) | US public domain / CC0 | `b72a658e68da4034e3edae845b2cc0974732fef4b3d5b82e1accd32c3acb59bc` |
| `usda_cooking_yields_meat_poultry.csv` | USDA Table of Cooking Yields for Meat & Poultry, release 2 (2014) — ars.usda.gov `/ARSUserFiles/80400535/Data/retn/USDA_CookingYields_MeatPoultry02.xlsx` (3 sheets flattened, `# sheet:` markers kept) | US public domain / CC0 | `72ec553e7d7590744f790591f20fc7a90664293a6834bdf4ee77c7af0158ab37` |
| `compendium_2024_adult_mets.csv` | 2024 Adult Compendium of Physical Activities — pacompendium.com category tables (22 categories, 1,111 activities). **Attribution required, values unaltered** — cite: Herrmann SD et al., "2024 Adult Compendium of Physical Activities", J Sport Health Sci 2024;13(1):6-12 | free incl. commercial use w/ attribution | `0617dfa125eebf405738bc4257a19bdeb3d9d26fb43985df9b24c792d293701d` |
| `fdc_foundation_subset.csv` | USDA FoodData Central bulk CSVs: Foundation Foods 2025-04-24 + SR Legacy 2018-04 (fdc.nal.usda.gov/download-datasets) — 49 base-ingredient foods × the nut-1 nutrient vocabulary, 886 per-100g rows; each row pins its `fdc_id` + `fdc_nutrient_nbr` | CC0 / US public domain | `928430a4bb0d07d9ee13c2efdf4cbb4d06ca50ab48655cf0d999c40d6db508e6` |

Labeled derivations inside `fdc_foundation_subset.csv` (the only
non-verbatim values, each named in its `derivation` column):

- `omega-3` = ALA (18:3 n-3) + EPA (20:5 n-3) + DHA (22:6 n-3) +
  DPA (22:5 n-3) summed — FDC carries the components, not the family
  total.
- `copper` converted FDC mg → module unit µg (×1000).
- `vitamin-b9` prefers Folate DFE (nbr 435), falls back to folate
  total (417).

Honest absences: FDC does not report chloride, boron, or silicon for
these foods — no rows exist rather than estimates. Foods FDC
Foundation lacks fall back to SR Legacy (`fdc_dataset` column says
which per row).

NOT vendored (license-blocked, per the plan's research verdicts):
Tandoor (Commons Clause), FooDB (NC), RecipeNLG/Recipe1M
(research-only), Monash FODMAP database (proprietary — published
cutoff VALUES may be cited as facts in nmp-2), WHO PDFs (NC-SA —
values citable as facts).

Related transcriptions that live as Python seeds (no machine format
exists upstream to vendor): `nutrition/dri_seed.py` (NASEM DRI/UL),
`nutrition/dga_limits.py` (DGA 2020-2025 + AMDR).

Fork-pins created for the adopted libraries (2026-08-20, licenses
verified via the GitHub license API): dausume/wger (AGPL-3.0),
dausume/recipe-scrapers (MIT, upstream 15.12.0),
dausume/ingredient-parser (MIT, upstream 2.7.0; PyPI package name
`ingredient-parser-nlp`). No requirements.txt pins yet — nothing
imports them until nmp-3 (the anti-dependency posture: a pin lands
with the code that uses it).

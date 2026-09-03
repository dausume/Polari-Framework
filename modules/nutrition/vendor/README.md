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
| `fdc_foundation_subset.csv` | USDA FoodData Central bulk CSVs: Foundation Foods 2025-04-24 + SR Legacy 2018-04 (fdc.nal.usda.gov/download-datasets) — 49 base-ingredient foods × the nut-1 nutrient vocabulary, 949 per-100g rows + 24 `sugars-total` rows added 2026-09-03 (N6, below) = 973; each row pins its `fdc_id` + `fdc_nutrient_nbr` | CC0 / US public domain | `32446be8c5131f4bd3d8ef293345308cc85479f5ba2194a60137df790c5ee135` |

Labeled derivations inside `fdc_foundation_subset.csv` (the only
non-verbatim values, each named in its `derivation` column):

- `omega-3` = ALA (18:3 n-3) + EPA (20:5 n-3) + DHA (22:6 n-3) +
  DPA (22:5 n-3) summed — FDC carries the components, not the family
  total.
- `copper` converted FDC mg → module unit µg (×1000).
- `vitamin-b9` prefers Folate DFE (nbr 435), falls back to folate
  total (417).
- `calories` prefers measured Energy (208), else Atwater General
  (957), else Atwater Specific (958) — newer Foundation entries
  publish energy only under the Atwater numbers.

**`sugars-total` rows (N6, retrieved 2026-09-03).** Total sugars so
the tracking readout can read "sweets" directly. Source: the SAME
bulk releases as the rest of the file (Foundation 2025-04-24 zip,
SR Legacy 2018-04 zip, `food_nutrient.csv` joined on each food's
existing `fdc_id`; the file's carbohydrate rows were re-derived from
those zips first — 49/49 match, proving the transcription path).
The FDC API (`api.nal.usda.gov/fdc/v1/food/{fdc_id}?api_key=DEMO_KEY`,
`format=abridged&nutrients=269`, 1 s apart) was tried first: it
answered 10 calls (almonds 4.35, beef chuck 0, black beans 2.12,
avocado = no row — all four agree with the bulk values) and then
returned HTTP 429 (DEMO_KEY rate limit) for the rest, so the bulk
CSVs carry every value. Two FDC total-sugars nutrients exist and the
`fdc_nutrient_nbr` column says which one each row is: **269**
(`Total Sugars`, id 2000 — the SR Legacy rows) or **269.3**
(`Sugars, Total`, id 1063 — the Foundation rows, which do not
publish 269; the `derivation` column names it). Values verbatim,
unit g. **24 of 49 foods** have a row; the other **25 have NO
total-sugars row in their FDC entry and get NO row** (never summed
from individual sugars, never estimated): avocado, banana, bell
pepper, carrot, celery, chickpeas, cod, cucumber, both flours,
garlic, ground beef 90, lentils, romaine, oats, pork loin, quinoa,
brown + white rice, salmon, salt, spinach, tofu, tomato, ground
turkey. These are TOTAL sugars, not added sugars — the DGA
added-sugar line cannot be read from them.

Two foods deliberately use SR Legacy over a Foundation match
(olive oil, black beans): their Foundation rows carry NO energy
nutrient at all, and energy anchors the whole chain. Salt has no
calories row — a true zero, not a gap.

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

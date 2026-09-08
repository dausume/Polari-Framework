"""
@module dmvdata.legal_sources_basis

The NON-GOVERNMENT legal source types (Dustin 2026-07-16: "add
NonProfitSource, CompanySource, PoliticalGroupSource, and
IndividualSource, basically varying legal source types") — siblings
of `GovSource` sharing its common core (name, short name, full name,
websites, key knobs, endpoint links) plus per-type LEGAL-IDENTITY
fields that point at the OFFICIAL verification registry for that
legal form:

  NonProfitSource       -> IRS Tax Exempt Organization Search (EIN)
  CompanySource         -> SEC EDGAR / state corporate registry
  PoliticalGroupSource  -> FEC committee lookup
  IndividualSource      -> a Polari Contributor row (platform users)

One machinery, five tables: the glossary/term-origin/retrieval/
credibility functions in dmvdata.gov_sources_basis span every source kind
via its SOURCE_TABLES registry. Non-government sources are always
FRAMED as such in reports — they are never presented as official
statistic origins.

Seeds carry ONLY organizations the plan doc already references, and
never invent registry identifiers: an unknown EIN/FEC id stays ''
with the lookup URL pointing at the official search tool.

@consumers
  - dmvdata.gov_sources_basis (SOURCE_TABLES machinery)
  - polariServer (registration + seed, wired by the main session)
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/legal_sources/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit

from dmvdata.objects.legal_sources._shared import POLITICAL_GROUP_KINDS, SEED_COMPANY_SOURCES, SEED_INDIVIDUAL_SOURCES, SEED_NONPROFIT_SOURCES, SEED_POLITICAL_SOURCES, _NOT_OFFICIAL  # noqa: F401
from dmvdata.objects.legal_sources.NonProfitSource import NonProfitSource  # noqa: F401
from dmvdata.objects.legal_sources.CompanySource import CompanySource  # noqa: F401
from dmvdata.objects.legal_sources.PoliticalGroupSource import PoliticalGroupSource  # noqa: F401
from dmvdata.objects.legal_sources.IndividualSource import IndividualSource  # noqa: F401
from dmvdata.objects.legal_sources.AcademicSource import AcademicSource  # noqa: F401
from dmvdata.objects.legal_sources.JournalisticSource import JournalisticSource  # noqa: F401

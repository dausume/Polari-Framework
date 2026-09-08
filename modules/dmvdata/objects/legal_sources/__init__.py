"""
@module dmvdata.objects.legal_sources

The legal_sources rows of dmvdata, one class per file: NonProfitSource, CompanySource, PoliticalGroupSource, IndividualSource, AcademicSource, JournalisticSource.
"""
from dmvdata.objects.legal_sources.NonProfitSource import NonProfitSource  # noqa: F401
from dmvdata.objects.legal_sources.CompanySource import CompanySource  # noqa: F401
from dmvdata.objects.legal_sources.PoliticalGroupSource import PoliticalGroupSource  # noqa: F401
from dmvdata.objects.legal_sources.IndividualSource import IndividualSource  # noqa: F401
from dmvdata.objects.legal_sources.AcademicSource import AcademicSource  # noqa: F401
from dmvdata.objects.legal_sources.JournalisticSource import JournalisticSource  # noqa: F401

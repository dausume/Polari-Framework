#    Copyright (C) 2020  Dustin Etts
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
CommercialSourcing Model

Sourcing through commercial purchase from vendors.

Key characteristic: This is NOT mutually exclusive with NaturalSourcing
or OpenSourceLocalSourcing. A vendor may produce materials using natural
or open-source methods and sell them commercially. This class focuses on
the purchasing relationship and vendor details.
"""

from objectTreeDecorators import treeObjectInit
from polariMaterialsScienceModule.materialSourcing.materialSourcing import MaterialSourcing


class CommercialSourcing(MaterialSourcing):
    """
    Commercial purchasing from vendors.

    Represents the ability to purchase a material from a vendor.
    NOT mutually exclusive with other sourcing types - vendors may use
    natural sourcing or open-source local methods to produce what they sell.

    Examples:
    - Industrial chemical supplier
    - Local maker selling naturally-sourced materials at farmer's market
    - Small business using open-source filament extruder to sell filament
    - Large manufacturer with proprietary processes

    Attributes:
        # Vendor information
        vendorName: Name of the vendor/supplier
        vendorType: Type (industrial, small_business, individual, cooperative)
        vendorContact: Contact information
        vendorWebsite: Website URL
        vendorLocation: Location (city, country)

        # Production method (links to other sourcing types)
        isCommercialOnly: True if vendor uses proprietary methods only (no natural/open-source)
        productionMethod: How vendor produces (natural, open_source, proprietary, unknown)
        naturalSourcingId: ID of NaturalSourcing if vendor uses natural methods
        openSourceSourcingId: ID of OpenSourceLocalSourcing if vendor uses OS methods
        productionTransparency: How transparent vendor is about production

        # Product information
        productName: Commercial product name
        productCode: Product code/SKU
        productGrade: Product grade
        technicalDataSheet: URL to technical data sheet
        safetyDataSheet: URL to safety data sheet (SDS/MSDS)

        # Pricing
        pricePerUnit: Price per unit
        priceUnit: Unit for pricing
        priceCurrency: Currency
        bulkDiscountAvailable: Whether bulk discounts available
        bulkPricing: Bulk pricing tiers description

        # Ordering
        orderingMethod: How to order (online, phone, email, in_person)
        minimumOrder: Minimum order quantity
        minimumOrderUnit: Unit for minimum order
        shippingOptions: Available shipping options
        typicalLeadTime: Typical lead time in days
        localPickupAvailable: Whether local pickup is available

        # Supply reliability
        stockReliability: Stock reliability (always, usually, sometimes, made_to_order)
        supplyChainRisk: Supply chain risk level (low, moderate, high)
        alternativeVendors: Known alternative vendors

        # Quality
        qualityConsistencyRating: Quality consistency (variable, moderate, consistent)
        batchCertificates: Whether batch certificates provided
        returnsAccepted: Whether returns accepted
        qualityGuarantee: Quality guarantee details

        # Vendor relationship
        accountRequired: Whether account required
        relationshipType: Relationship (one_time, recurring, contract)
        supportQuality: Quality of vendor support

        # Ethics/sustainability
        ethicalSourcing: Whether vendor practices ethical sourcing
        sustainabilityCertifications: Sustainability certifications
        localBusiness: Whether vendor is a local business
        supportsCommunity: Whether vendor supports local community

        Inherits all from MaterialSourcing
    """

    SOURCING_TYPE = 'commercial'

    @treeObjectInit
    def __init__(self,
                 manager=None,
                 branch=None,
                 id=None,
                 rawMaterialId='',
                 name='',
                 description='',
                 availability='common',
                 leadTime=0,
                 minimumOrderQuantity=0.0,
                 minimumOrderUnit='kg',
                 estimatedCostPerUnit=0.0,
                 costUnit='kg',
                 costCurrency='USD',
                 geographicRegion='',
                 locallyAvailable=False,
                 sustainabilityRating='fair',
                 renewableSource=False,
                 carbonFootprint='',
                 qualityConsistency='consistent',
                 certifications='',
                 notes='',
                 # Vendor information
                 vendorName='',
                 vendorType='industrial',
                 vendorContact='',
                 vendorWebsite='',
                 vendorLocation='',
                 # Production method
                 isCommercialOnly=False,
                 productionMethod='unknown',
                 naturalSourcingId='',
                 openSourceSourcingId='',
                 productionTransparency='low',
                 # Product information
                 productName='',
                 productCode='',
                 productGrade='',
                 technicalDataSheet='',
                 safetyDataSheet='',
                 # Pricing
                 pricePerUnit=0.0,
                 priceUnit='kg',
                 priceCurrency='USD',
                 bulkDiscountAvailable=False,
                 bulkPricing='',
                 # Ordering
                 orderingMethod='online',
                 minimumOrder=0.0,
                 minimumOrderOrderUnit='kg',
                 shippingOptions='',
                 typicalLeadTime=0,
                 localPickupAvailable=False,
                 # Supply reliability
                 stockReliability='usually',
                 supplyChainRisk='low',
                 alternativeVendors='',
                 # Quality
                 qualityConsistencyRating='consistent',
                 batchCertificates=False,
                 returnsAccepted=False,
                 qualityGuarantee='',
                 # Vendor relationship
                 accountRequired=False,
                 relationshipType='one_time',
                 supportQuality='fair',
                 # Ethics/sustainability
                 ethicalSourcing=False,
                 sustainabilityCertifications='',
                 localBusiness=False,
                 supportsCommunity=False):
        MaterialSourcing.__init__(
            self, manager=manager, branch=branch, id=id,
            rawMaterialId=rawMaterialId, sourcingType='commercial',
            name=name, description=description,
            availability=availability, leadTime=leadTime,
            minimumOrderQuantity=minimumOrderQuantity,
            minimumOrderUnit=minimumOrderUnit,
            estimatedCostPerUnit=estimatedCostPerUnit,
            costUnit=costUnit, costCurrency=costCurrency,
            geographicRegion=geographicRegion,
            locallyAvailable=locallyAvailable,
            sustainabilityRating=sustainabilityRating,
            renewableSource=renewableSource,
            carbonFootprint=carbonFootprint,
            qualityConsistency=qualityConsistency,
            certifications=certifications, notes=notes)

        # Vendor information
        self.vendorName = vendorName
        self.vendorType = vendorType
        self.vendorContact = vendorContact
        self.vendorWebsite = vendorWebsite
        self.vendorLocation = vendorLocation

        # Production method
        self.isCommercialOnly = isCommercialOnly
        self.productionMethod = productionMethod
        self.naturalSourcingId = naturalSourcingId
        self.openSourceSourcingId = openSourceSourcingId
        self.productionTransparency = productionTransparency

        # Product information
        self.productName = productName
        self.productCode = productCode
        self.productGrade = productGrade
        self.technicalDataSheet = technicalDataSheet
        self.safetyDataSheet = safetyDataSheet

        # Pricing
        self.pricePerUnit = pricePerUnit
        self.priceUnit = priceUnit
        self.priceCurrency = priceCurrency
        self.bulkDiscountAvailable = bulkDiscountAvailable
        self.bulkPricing = bulkPricing

        # Ordering
        self.orderingMethod = orderingMethod
        self.minimumOrder = minimumOrder
        self.minimumOrderOrderUnit = minimumOrderOrderUnit
        self.shippingOptions = shippingOptions
        self.typicalLeadTime = typicalLeadTime
        self.localPickupAvailable = localPickupAvailable

        # Supply reliability
        self.stockReliability = stockReliability
        self.supplyChainRisk = supplyChainRisk
        self.alternativeVendors = alternativeVendors

        # Quality
        self.qualityConsistencyRating = qualityConsistencyRating
        self.batchCertificates = batchCertificates
        self.returnsAccepted = returnsAccepted
        self.qualityGuarantee = qualityGuarantee

        # Vendor relationship
        self.accountRequired = accountRequired
        self.relationshipType = relationshipType
        self.supportQuality = supportQuality

        # Ethics/sustainability
        self.ethicalSourcing = ethicalSourcing
        self.sustainabilityCertifications = sustainabilityCertifications
        self.localBusiness = localBusiness
        self.supportsCommunity = supportsCommunity

    def __repr__(self):
        return f"CommercialSourcing(id='{self.id}', vendor='{self.vendorName}', method='{self.productionMethod}')"

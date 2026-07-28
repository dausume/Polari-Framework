"""
@module bizops.bizops_basis

Business operations as DATA (biz-1, Dustin 2026-07-28): how a
business starts, how it upgrades, how the local economy progresses
toward a functioning baseline, and the production-planning rows the
order planner runs on.

The canonical origin (an axiom of the model, seeded not assumed):
EVERY business starts as ONE PERSON buying from whatever is
available and selling only in off-time — online or at farmer/maker
markets. Everything after that is discrete UPGRADE STEPS with
evidence gates, never silent growth.

@consumers polariServer defClassList + seed_pairs, bizops.*
"""

from objectTreeDecorators import treeObject, treeObjectInit

UPGRADE_KINDS = ('hire-role', 'process-change', 'add-capability')
ORDER_STATUSES = ('requested', 'accepted', 'deferred', 'refused',
                  'done')


class BusinessStageDefinition(treeObject):
    """One rung of the business ladder: headcount, committed hours,
    sales channels and sourcing posture AT that rung."""

    @treeObjectInit
    def __init__(self, name='', stage_index=0, display_name='',
                 headcount=1, weekly_hours=10.0,
                 time_commitment='off-time',
                 sales_channels_json='[]',
                 sourcing_posture='retail-available',
                 capabilities_json='[]', is_prior=True,
                 provenance_id='biz-1', notes='', manager=None):
        self.name = name
        self.stage_index = stage_index
        self.display_name = display_name
        self.headcount = headcount
        #: Productive hours/week the stage can actually field.
        self.weekly_hours = weekly_hours
        self.time_commitment = time_commitment
        self.sales_channels_json = sales_channels_json
        #: retail-available | bulk | local-partners |
        #: self-made-intermediaries — where inputs come from.
        self.sourcing_posture = sourcing_posture
        self.capabilities_json = capabilities_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class BusinessUpgradeStep(treeObject):
    """One discrete upgrade EDGE: hire a person onto a task, change
    a process, or add a capability — with the evidence gate that
    should be TRUE before taking it (gates are suggestions with
    evidence, never auto-applied)."""

    @treeObjectInit
    def __init__(self, name='', display_name='', from_stage='',
                 to_stage='', kind='process-change',
                 role_or_capability='', evidence_gate='',
                 effects_json='{}', is_prior=True,
                 provenance_id='biz-1', notes='', manager=None):
        self.name = name
        self.display_name = display_name
        self.from_stage = from_stage
        #: '' = stays on the same stage (capability adds).
        self.to_stage = to_stage
        self.kind = (kind if kind in UPGRADE_KINDS
                     else 'process-change')
        self.role_or_capability = role_or_capability
        #: Plain-language condition the flow report evaluates or
        #: surfaces (e.g. 'backlog exceeds capacity two plans
        #: running').
        self.evidence_gate = evidence_gate
        #: JSON: {weekly_hours_delta, weekly_cost_delta,
        #: capabilities_added: [...]} — what taking the step does.
        self.effects_json = effects_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class BusinessProfile(treeObject):
    """A LIVE business: which model it runs, which rung it is on,
    which capabilities it actually has today."""

    @treeObjectInit
    def __init__(self, name='', display_name='',
                 business_model_ref='', current_stage='',
                 headcount=1, weekly_hours=10.0,
                 capabilities_json='[]', region_note='',
                 is_prior=True, provenance_id='biz-1', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.business_model_ref = business_model_ref
        self.current_stage = current_stage
        self.headcount = headcount
        self.weekly_hours = weekly_hours
        self.capabilities_json = capabilities_json
        self.region_note = region_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class LocalEconomyMilestone(treeObject):
    """One rung of the LOCAL ECONOMY track toward a functioning
    local economic baseline (the OSEB made operational). Status is
    DERIVED from live rows by kind — never hand-flipped."""

    @treeObjectInit
    def __init__(self, name='', display_name='', track_order=0,
                 kind='', target_ref='', description='',
                 is_prior=True, provenance_id='biz-1', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.track_order = track_order
        #: local-available-source-for | makeable-intermediary |
        #: mutual-loop-exists | business-at-stage | reclaim-active |
        #: crush-loop-logged — each evaluated against live tables.
        self.kind = kind
        self.target_ref = target_ref
        self.description = description
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ProcessWorkflowDefinition(treeObject):
    """A generic production workflow (wax-mold printing, geopolymer
    casting in wax molds, ceramic molds from wax masters) with
    volume-scaled labor priors — hours are FLAGGED estimates until
    timed runs replace them."""

    @treeObjectInit
    def __init__(self, name='', display_name='',
                 product_item_ref='', mold_strategy='',
                 hours_per_unit_ref=0.0, hours_per_mold_ref=0.0,
                 passive_hours_per_batch=0.0,
                 volume_exponent=0.667, steps_json='[]',
                 is_prior=True, provenance_id='biz-1', notes='',
                 manager=None):
        self.name = name
        self.display_name = display_name
        self.product_item_ref = product_item_ref
        #: MOLD_STRATEGY_PRIORS key this workflow rides on.
        self.mold_strategy = mold_strategy
        #: Attended hours per unit at the 1 L reference size.
        self.hours_per_unit_ref = hours_per_unit_ref
        #: Attended hours to MAKE one mold at reference size.
        self.hours_per_mold_ref = hours_per_mold_ref
        #: Unattended time (cure, firing) — gates throughput, not
        #: labor.
        self.passive_hours_per_batch = passive_hours_per_batch
        #: Shell-dominated ops scale ~V^(2/3).
        self.volume_exponent = volume_exponent
        self.steps_json = steps_json
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes


class ProductOrder(treeObject):
    """The order REGISTRAR row the planner runs on. v1 rows are
    entered directly (CRUDE/UI); the od-4 sale.order binding is the
    designed feed from Odoo once orders live there."""

    @treeObjectInit
    def __init__(self, name='', product_item_ref='',
                 variant_note='', unit_volume_l=1.0, quantity=0,
                 due_days=30, status='requested', customer_note='',
                 is_prior=False, provenance_id='biz-1', notes='',
                 manager=None):
        self.name = name
        self.product_item_ref = product_item_ref
        self.variant_note = variant_note
        #: The SIZE variable — everything scales from it.
        self.unit_volume_l = unit_volume_l
        self.quantity = quantity
        self.due_days = due_days
        self.status = (status if status in ORDER_STATUSES
                       else 'requested')
        self.customer_note = customer_note
        self.is_prior = is_prior
        self.provenance_id = provenance_id
        self.notes = notes

"""
@module mech.objects.assembly.MechContact

Row class MechContact of the mech module — one class per file (design §7); mxc-2.
The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit
from mech.objects.assembly._shared import CONTACT_KINDS

class MechContact(treeObject):
    """A friction-bearing contact between two instances — the row the
    1-DOF motion engine (mxc-4) reads μ from. Not a joint: a bin
    resting on a baseplate, a drawer side on its runner."""

    @treeObjectInit
    def __init__(self, name='', assembly_ref='', instance_a='',
                 instance_b='', kind='static', mu_json='{}',
                 normal_axis_json='[0, 0, 1]', notes='', is_prior=True,
                 provenance_id='', manager=None):
        self.name = name
        self.assembly_ref = assembly_ref
        self.instance_a = instance_a
        self.instance_b = instance_b
        #: CONTACT_KINDS: sliding | rolling | static.
        self.kind = kind if kind in CONTACT_KINDS else 'static'
        #: {static, kinetic, basis} — knobs until measured; basis
        #: names the pairing ('UHMWPE on aluminium, cited') so a
        #: prior never passes as a measurement.
        self.mu_json = mu_json
        #: Contact normal in the assembly frame (unit vector).
        self.normal_axis_json = normal_axis_json
        self.notes = notes
        self.is_prior = is_prior
        self.provenance_id = provenance_id

"""
@module collab.objects.collab.CollaborationSession

Row class CollaborationSession of the collab module — one class per file (design §7), split
from collab_basis.py (sap-2c). The class docstring below is the explanation.
"""
from objectTreeDecorators import treeObject, treeObjectInit

class CollaborationSession(treeObject):
    """A meeting room's identity + policy. The room EXISTS as a row
    first; LiveKit only ever sees tokens this backend minted for it."""

    @treeObjectInit
    def __init__(self, name='', title='', room_name='', scope='local',
                 status='open', moderator_subject='',
                 moderator_username='', moderator_role='',
                 moderator_source='', bound_route='', bound_ref='',
                 notes='', manager=None):
        self.name = name
        self.title = title
        # mtg-6: WHICH SURFACE this meeting belongs to, as data.
        # bound_route is a page path ('/sim-spaces/motor-m2-viz'), so a
        # page can ask "is there a meeting about what I am showing?"
        # without anything being hardcoded on either side; bound_ref is
        # the object itself ('SimSpaceDefinition/motor-m2-viz') for the
        # cases where several routes show one object. Both empty = a
        # standalone meeting, which is the ordinary case.
        self.bound_route = bound_route
        self.bound_ref = bound_ref
        # LiveKit room identity; defaults to the row name at token
        # time so a bare CRUDE create still yields a joinable room.
        self.room_name = room_name
        self.scope = scope
        self.status = status
        # Moderation: empty until the first VERIFIED caller mints a
        # token and self-claims (first-come PRIMARY, the
        # group-authority precedent). moderator_role additionally
        # grants moderation to any caller carrying that KC role.
        self.moderator_subject = moderator_subject
        self.moderator_username = moderator_username
        self.moderator_role = moderator_role
        # How the moderator identity was established — evidence.
        self.moderator_source = moderator_source
        self.notes = notes

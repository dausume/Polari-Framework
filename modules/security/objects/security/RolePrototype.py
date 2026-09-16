"""
@module security.objects.security.RolePrototype

Row class RolePrototype of the security module — one class per file.
"""
from objectTreeDecorators import treeObject, treeObjectInit


class RolePrototype(treeObject):
    """A PROTOTYPE ROLE (his ask 2026-09-16): a role that exists to be role-played. Acting as it in dev mode lets
    the person do anything while everything they touch is recorded against the role; the review becomes the
    template a permissions admin concretes into an enforced group (AppPermissionProfile + KC group), after which
    the recording is replayed to prove the role can still do its job. State moves prototype → concreted → enforced."""

    @treeObjectInit
    def __init__(self, name: str = '', title: str = '', description: str = '', state: str = 'prototype', created_by: str = '',
                 created_at: str = '', concreted_profile: str = '', concreted_at: str = '', verified_at: str = '', verified_verdict: str = ''):
        self.name = name                        # the role id, lower-case ('journalist')
        self.title = title
        self.description = description
        self.state = state                      # prototype | concreted | enforced
        self.created_by = created_by
        self.created_at = created_at
        self.concreted_profile = concreted_profile   # the AppPermissionProfile name it was concreted into
        self.concreted_at = concreted_at
        self.verified_at = verified_at
        self.verified_verdict = verified_verdict

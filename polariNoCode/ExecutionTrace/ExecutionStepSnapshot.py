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
ExecutionStepSnapshot models for Polari No-Code System

Serializable snapshots capturing context/state at each point in a
solution's execution.

Classes:
    InstanceContextSnapshot - Serializable snapshot of execution context
    VariableChange - A single variable change between two snapshots
    ObjectChange - A single object change between two snapshots
    ContextDiff - Diff between before and after context snapshots
    ExecutionStepSnapshot - Full diagnostic state at a single execution step
"""

import json
from datetime import datetime, timezone


class InstanceContextSnapshot:
    """Serializable snapshot of execution context at a point in time."""

    def __init__(self, state_name, solution_name, execution_id,
                 variables=None, objects=None, captured_at=None):
        self.state_name = state_name
        self.solution_name = solution_name
        self.execution_id = execution_id
        self.variables = variables or {}  # { name: InstanceVariableSnapshot dict }
        self.objects = objects or {}      # { id: InstanceObjectSnapshot dict }
        self.captured_at = captured_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            'stateName': self.state_name,
            'solutionName': self.solution_name,
            'executionId': self.execution_id,
            'variables': self.variables,
            'objects': self.objects,
            'capturedAt': self.captured_at,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            state_name=data.get('stateName', ''),
            solution_name=data.get('solutionName', ''),
            execution_id=data.get('executionId', ''),
            variables=data.get('variables', {}),
            objects=data.get('objects', {}),
            captured_at=data.get('capturedAt'),
        )


class VariableChange:
    """A single variable change between two context snapshots."""

    def __init__(self, name, change_type, previous_value=None, new_value=None,
                 previous_type=None, new_type=None):
        """
        Args:
            change_type: 'added', 'modified', or 'removed'
        """
        self.name = name
        self.change_type = change_type
        self.previous_value = previous_value
        self.new_value = new_value
        self.previous_type = previous_type
        self.new_type = new_type

    def to_dict(self):
        d = {
            'name': self.name,
            'changeType': self.change_type,
        }
        if self.previous_value is not None:
            d['previousValue'] = self.previous_value
        if self.new_value is not None:
            d['newValue'] = self.new_value
        if self.previous_type is not None:
            d['previousType'] = self.previous_type
        if self.new_type is not None:
            d['newType'] = self.new_type
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get('name', ''),
            change_type=data.get('changeType', ''),
            previous_value=data.get('previousValue'),
            new_value=data.get('newValue'),
            previous_type=data.get('previousType'),
            new_type=data.get('newType'),
        )


class ObjectChange:
    """A single object change between two context snapshots."""

    def __init__(self, instance_id, class_name, change_type,
                 previous_data=None, new_data=None):
        self.instance_id = instance_id
        self.class_name = class_name
        self.change_type = change_type
        self.previous_data = previous_data
        self.new_data = new_data

    def to_dict(self):
        d = {
            'instanceId': self.instance_id,
            'className': self.class_name,
            'changeType': self.change_type,
        }
        if self.previous_data is not None:
            d['previousData'] = self.previous_data
        if self.new_data is not None:
            d['newData'] = self.new_data
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(
            instance_id=data.get('instanceId', ''),
            class_name=data.get('className', ''),
            change_type=data.get('changeType', ''),
            previous_data=data.get('previousData'),
            new_data=data.get('newData'),
        )


class ContextDiff:
    """Diff between before and after context snapshots."""

    def __init__(self, variable_changes=None, object_changes=None):
        self.variable_changes = variable_changes or []
        self.object_changes = object_changes or []

    @property
    def has_changes(self):
        return self.total_change_count > 0

    @property
    def total_change_count(self):
        return len(self.variable_changes) + len(self.object_changes)

    @staticmethod
    def compute(before, after):
        """Compute the diff between two InstanceContextSnapshot instances."""
        variable_changes = []
        object_changes = []

        before_vars = before.variables if isinstance(before.variables, dict) else {}
        after_vars = after.variables if isinstance(after.variables, dict) else {}

        # Added / modified variables
        for name, after_var in after_vars.items():
            before_var = before_vars.get(name)
            if before_var is None:
                variable_changes.append(VariableChange(
                    name=name,
                    change_type='added',
                    new_value=after_var.get('value') if isinstance(after_var, dict) else None,
                    new_type=after_var.get('type') if isinstance(after_var, dict) else None,
                ))
            else:
                bval = json.dumps(before_var.get('value') if isinstance(before_var, dict) else before_var, default=str)
                aval = json.dumps(after_var.get('value') if isinstance(after_var, dict) else after_var, default=str)
                if bval != aval:
                    variable_changes.append(VariableChange(
                        name=name,
                        change_type='modified',
                        previous_value=before_var.get('value') if isinstance(before_var, dict) else None,
                        new_value=after_var.get('value') if isinstance(after_var, dict) else None,
                        previous_type=before_var.get('type') if isinstance(before_var, dict) else None,
                        new_type=after_var.get('type') if isinstance(after_var, dict) else None,
                    ))

        # Removed variables
        for name in before_vars:
            if name not in after_vars:
                before_var = before_vars[name]
                variable_changes.append(VariableChange(
                    name=name,
                    change_type='removed',
                    previous_value=before_var.get('value') if isinstance(before_var, dict) else None,
                    previous_type=before_var.get('type') if isinstance(before_var, dict) else None,
                ))

        before_objs = before.objects if isinstance(before.objects, dict) else {}
        after_objs = after.objects if isinstance(after.objects, dict) else {}

        # Added / modified objects
        for oid, after_obj in after_objs.items():
            before_obj = before_objs.get(oid)
            if before_obj is None:
                object_changes.append(ObjectChange(
                    instance_id=oid,
                    class_name=after_obj.get('className', '') if isinstance(after_obj, dict) else '',
                    change_type='added',
                    new_data=after_obj.get('data') if isinstance(after_obj, dict) else None,
                ))
            else:
                bdata = json.dumps(before_obj.get('data') if isinstance(before_obj, dict) else before_obj, default=str)
                adata = json.dumps(after_obj.get('data') if isinstance(after_obj, dict) else after_obj, default=str)
                if bdata != adata:
                    object_changes.append(ObjectChange(
                        instance_id=oid,
                        class_name=after_obj.get('className', '') if isinstance(after_obj, dict) else '',
                        change_type='modified',
                        previous_data=before_obj.get('data') if isinstance(before_obj, dict) else None,
                        new_data=after_obj.get('data') if isinstance(after_obj, dict) else None,
                    ))

        # Removed objects
        for oid in before_objs:
            if oid not in after_objs:
                before_obj = before_objs[oid]
                object_changes.append(ObjectChange(
                    instance_id=oid,
                    class_name=before_obj.get('className', '') if isinstance(before_obj, dict) else '',
                    change_type='removed',
                    previous_data=before_obj.get('data') if isinstance(before_obj, dict) else None,
                ))

        return ContextDiff(
            variable_changes=variable_changes,
            object_changes=object_changes,
        )

    def to_dict(self):
        return {
            'variableChanges': [vc.to_dict() for vc in self.variable_changes],
            'objectChanges': [oc.to_dict() for oc in self.object_changes],
            'hasChanges': self.has_changes,
            'totalChangeCount': self.total_change_count,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            variable_changes=[VariableChange.from_dict(v) for v in data.get('variableChanges', [])],
            object_changes=[ObjectChange.from_dict(o) for o in data.get('objectChanges', [])],
        )


class ExecutionStepSnapshot:
    """Full diagnostic state at a single execution step."""

    def __init__(
        self,
        snapshot_id,
        step_index,
        state_name,
        state_class_name,
        state_display_name='',
        context_before=None,
        context_after=None,
        context_diff=None,
        status='pending',
        execution_result=None,
        execution_error=None,
        start_time=None,
        end_time=None,
        duration_ms=None,
        branch_path=None,
        branch_taken=None,
        branch_label=None,
        loop_iteration_index=None,
        enclosing_loop_state_name=None,
        hit_breakpoint=False,
        log_output=None,
    ):
        self.snapshot_id = snapshot_id
        self.step_index = step_index
        self.state_name = state_name
        self.state_class_name = state_class_name
        self.state_display_name = state_display_name or state_name
        self.context_before = context_before
        self.context_after = context_after
        self.context_diff = context_diff
        self.status = status  # pending | running | completed | errored | skipped
        self.execution_result = execution_result
        self.execution_error = execution_error
        self.start_time = start_time or datetime.now(timezone.utc).isoformat()
        self.end_time = end_time
        self.duration_ms = duration_ms
        self.branch_path = branch_path or []
        self.branch_taken = branch_taken
        self.branch_label = branch_label
        self.loop_iteration_index = loop_iteration_index
        self.enclosing_loop_state_name = enclosing_loop_state_name
        self.hit_breakpoint = hit_breakpoint
        self.log_output = log_output or []

    def to_dict(self):
        d = {
            'snapshotId': self.snapshot_id,
            'stepIndex': self.step_index,
            'stateName': self.state_name,
            'stateClassName': self.state_class_name,
            'stateDisplayName': self.state_display_name,
            'status': self.status,
            'startTime': self.start_time,
            'hitBreakpoint': self.hit_breakpoint,
            'branchPath': self.branch_path,
        }
        if self.context_before:
            d['contextBefore'] = (
                self.context_before.to_dict()
                if hasattr(self.context_before, 'to_dict')
                else self.context_before
            )
        if self.context_after:
            d['contextAfter'] = (
                self.context_after.to_dict()
                if hasattr(self.context_after, 'to_dict')
                else self.context_after
            )
        if self.context_diff:
            d['contextDiff'] = (
                self.context_diff.to_dict()
                if hasattr(self.context_diff, 'to_dict')
                else self.context_diff
            )
        if self.execution_result is not None:
            d['executionResult'] = self.execution_result
        if self.execution_error is not None:
            d['executionError'] = self.execution_error
        if self.end_time:
            d['endTime'] = self.end_time
        if self.duration_ms is not None:
            d['durationMs'] = self.duration_ms
        if self.branch_taken is not None:
            d['branchTaken'] = self.branch_taken
        if self.branch_label is not None:
            d['branchLabel'] = self.branch_label
        if self.loop_iteration_index is not None:
            d['loopIterationIndex'] = self.loop_iteration_index
        if self.enclosing_loop_state_name is not None:
            d['enclosingLoopStateName'] = self.enclosing_loop_state_name
        if self.log_output:
            d['logOutput'] = self.log_output
        return d

    @classmethod
    def from_dict(cls, data):
        context_before = None
        if data.get('contextBefore'):
            context_before = InstanceContextSnapshot.from_dict(data['contextBefore'])

        context_after = None
        if data.get('contextAfter'):
            context_after = InstanceContextSnapshot.from_dict(data['contextAfter'])

        context_diff = None
        if data.get('contextDiff'):
            context_diff = ContextDiff.from_dict(data['contextDiff'])

        return cls(
            snapshot_id=data.get('snapshotId', ''),
            step_index=data.get('stepIndex', 0),
            state_name=data.get('stateName', ''),
            state_class_name=data.get('stateClassName', ''),
            state_display_name=data.get('stateDisplayName', ''),
            context_before=context_before,
            context_after=context_after,
            context_diff=context_diff,
            status=data.get('status', 'pending'),
            execution_result=data.get('executionResult'),
            execution_error=data.get('executionError'),
            start_time=data.get('startTime'),
            end_time=data.get('endTime'),
            duration_ms=data.get('durationMs'),
            branch_path=data.get('branchPath', []),
            branch_taken=data.get('branchTaken'),
            branch_label=data.get('branchLabel'),
            loop_iteration_index=data.get('loopIterationIndex'),
            enclosing_loop_state_name=data.get('enclosingLoopStateName'),
            hit_breakpoint=data.get('hitBreakpoint', False),
            log_output=data.get('logOutput', []),
        )

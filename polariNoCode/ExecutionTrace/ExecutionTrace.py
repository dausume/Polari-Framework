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
ExecutionTrace model for Polari No-Code System

Complete ordered record of one execution run, collecting
ExecutionStepSnapshots in sequence.
"""

from datetime import datetime, timezone
from polariNoCode.ExecutionTrace.ExecutionStepSnapshot import ExecutionStepSnapshot


class ExecutionTrace:
    """Complete ordered record of one execution run."""

    def __init__(self, execution_id, solution_name, target_runtime):
        self.execution_id = execution_id
        self.solution_name = solution_name
        self.target_runtime = target_runtime
        self.status = 'running'  # running | completed | errored | cancelled
        self.steps = []
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at = None
        self.final_return_value = None
        self.error_summary = None

    def add_step(self, snapshot):
        """Append an ExecutionStepSnapshot to the trace."""
        self.steps.append(snapshot)

    def get_step_at(self, index):
        """Get snapshot at a given index, or None."""
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None

    def get_snapshots_for_state(self, state_name):
        """Return all snapshots for a given state name."""
        return [s for s in self.steps if s.state_name == state_name]

    def get_latest_snapshot_for_state(self, state_name):
        """Return the most recent snapshot for a given state name, or None."""
        matches = self.get_snapshots_for_state(state_name)
        return matches[-1] if matches else None

    def get_current_step(self):
        """Return the last step in the trace, or None."""
        return self.steps[-1] if self.steps else None

    def complete(self, final_return_value=None):
        """Mark the trace as completed."""
        self.status = 'completed'
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.final_return_value = final_return_value

    def error(self, error_summary):
        """Mark the trace as errored."""
        self.status = 'errored'
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.error_summary = error_summary

    def cancel(self):
        """Mark the trace as cancelled."""
        self.status = 'cancelled'
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        d = {
            'executionId': self.execution_id,
            'solutionName': self.solution_name,
            'targetRuntime': self.target_runtime,
            'status': self.status,
            'steps': [
                (s.to_dict() if hasattr(s, 'to_dict') else s)
                for s in self.steps
            ],
            'startedAt': self.started_at,
        }
        if self.completed_at:
            d['completedAt'] = self.completed_at
        if self.final_return_value is not None:
            d['finalReturnValue'] = self.final_return_value
        if self.error_summary is not None:
            d['errorSummary'] = self.error_summary
        return d

    @classmethod
    def from_dict(cls, data):
        trace = cls(
            execution_id=data.get('executionId', ''),
            solution_name=data.get('solutionName', ''),
            target_runtime=data.get('targetRuntime', 'python_backend'),
        )
        trace.status = data.get('status', 'running')
        trace.started_at = data.get('startedAt', trace.started_at)
        trace.completed_at = data.get('completedAt')
        trace.final_return_value = data.get('finalReturnValue')
        trace.error_summary = data.get('errorSummary')
        trace.steps = [
            ExecutionStepSnapshot.from_dict(s) if isinstance(s, dict) else s
            for s in data.get('steps', [])
        ]
        return trace

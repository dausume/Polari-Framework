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
DebugSession model for Polari No-Code System

Manages interactive stepping and breakpoints for debugging
a solution execution.
"""

from polariNoCode.ExecutionTrace.ExecutionTrace import ExecutionTrace


class Breakpoint:
    """A breakpoint on a state."""

    def __init__(self, state_name, condition=None, enabled=True, hit_count=0):
        self.state_name = state_name
        self.condition = condition
        self.enabled = enabled
        self.hit_count = hit_count

    def to_dict(self):
        d = {
            'stateName': self.state_name,
            'enabled': self.enabled,
            'hitCount': self.hit_count,
        }
        if self.condition is not None:
            d['condition'] = self.condition
        return d

    @classmethod
    def from_dict(cls, data):
        return cls(
            state_name=data.get('stateName', ''),
            condition=data.get('condition'),
            enabled=data.get('enabled', True),
            hit_count=data.get('hitCount', 0),
        )


class DebugSession:
    """Manages interactive stepping and breakpoints."""

    def __init__(self, session_id, trace):
        self.session_id = session_id
        self.trace = trace
        self.breakpoints = {}  # { state_name: Breakpoint }
        self.viewing_step_index = -1
        self.status = 'idle'  # idle | running | paused | stepping | completed | errored
        self.stepping_mode = 'run'  # run | step_over | step_into | pause | step_back
        self.follow_live = True

    # --- Breakpoint management ---

    def add_breakpoint(self, state_name, condition=None):
        bp = Breakpoint(state_name=state_name, condition=condition)
        self.breakpoints[state_name] = bp
        return bp

    def remove_breakpoint(self, state_name):
        return self.breakpoints.pop(state_name, None) is not None

    def toggle_breakpoint(self, state_name):
        bp = self.breakpoints.get(state_name)
        if bp:
            bp.enabled = not bp.enabled

    def should_break_at(self, state_name, context=None):
        """Check if execution should pause at the given state."""
        bp = self.breakpoints.get(state_name)
        if bp is None or not bp.enabled:
            return False
        # If no condition, always break
        if not bp.condition:
            bp.hit_count += 1
            return True
        # Evaluate condition against context (basic eval)
        if context is not None:
            try:
                ctx_dict = context if isinstance(context, dict) else {}
                result = eval(bp.condition, {"__builtins__": {}}, ctx_dict)
                if result:
                    bp.hit_count += 1
                    return True
            except Exception:
                # On evaluation error, break anyway for safety
                bp.hit_count += 1
                return True
        return False

    # --- Live execution ---

    def on_step_completed(self, snapshot):
        """Called when a new step snapshot arrives."""
        self.trace.add_step(snapshot)
        if self.follow_live:
            self.viewing_step_index = len(self.trace.steps) - 1
        if snapshot.hit_breakpoint:
            self.status = 'paused'
            self.stepping_mode = 'pause'

    # --- Serialization ---

    def to_dict(self):
        return {
            'sessionId': self.session_id,
            'trace': self.trace.to_dict(),
            'breakpoints': [bp.to_dict() for bp in self.breakpoints.values()],
            'viewingStepIndex': self.viewing_step_index,
            'status': self.status,
            'steppingMode': self.stepping_mode,
            'followLive': self.follow_live,
        }

    @classmethod
    def from_dict(cls, data):
        trace = ExecutionTrace.from_dict(data.get('trace', {}))
        session = cls(
            session_id=data.get('sessionId', ''),
            trace=trace,
        )
        session.viewing_step_index = data.get('viewingStepIndex', -1)
        session.status = data.get('status', 'idle')
        session.stepping_mode = data.get('steppingMode', 'run')
        session.follow_live = data.get('followLive', True)

        for bp_data in data.get('breakpoints', []):
            bp = Breakpoint.from_dict(bp_data)
            session.breakpoints[bp.state_name] = bp

        return session

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
Stepping functions for Polari No-Code execution.

Standardized checkpoint functions inserted between states in generated code.
Configurable via StepConfig for step control, performance recording,
and future extensibility.
"""

import copy
import time


class StepConfig:
    """Configuration for step checkpoint behavior."""

    def __init__(self, mode='run', record_timing=False, record_context=True,
                 record_memory=False, custom_tags=None):
        self.mode = mode                    # 'run' | 'step' | 'performance'
        self.record_timing = record_timing
        self.record_context = record_context
        self.record_memory = record_memory
        self.custom_tags = custom_tags or {}

    def to_dict(self):
        return {
            'mode': self.mode,
            'recordTiming': self.record_timing,
            'recordContext': self.record_context,
            'recordMemory': self.record_memory,
            'customTags': self.custom_tags,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            mode=data.get('mode', 'run'),
            record_timing=data.get('recordTiming', False),
            record_context=data.get('recordContext', True),
            record_memory=data.get('recordMemory', False),
            custom_tags=data.get('customTags', {}),
        )


def step_checkpoint(step_index, state_name, state_class, context,
                    config=None, trace_collector=None):
    """
    Standardized checkpoint inserted between states in generated code.

    In 'run' mode: minimal overhead (just timestamp).
    In 'step' mode: captures full context snapshot.
    In 'performance' mode: captures timing + optional memory.

    Args:
        step_index: Sequential step number
        state_name: Name of the current state
        state_class: Class/type of the current state (e.g. 'VariableAssignment')
        context: Current execution context (dict of local variables)
        config: Optional StepConfig for controlling capture behavior
        trace_collector: Optional list to append the step record to

    Returns:
        A step record dict.
    """
    record = {
        'step_index': step_index,
        'state_name': state_name,
        'state_class': state_class,
        'timestamp': time.time(),
    }

    if config and config.record_timing:
        record['timing'] = {'wall_time': time.perf_counter()}

    if not config or config.record_context:
        record['context_snapshot'] = copy.deepcopy(context)

    if config and config.custom_tags:
        record['custom_tags'] = config.custom_tags

    if trace_collector is not None:
        trace_collector.append(record)

    return record

"""
@module hwfpga.fpga_api

Knob surface for the FPGA register maps (hwsim-3). Reads only — the
knobs themselves are the RegisterMapDefinition / RegisterDefinition
rows, edited through the standard CRUDE surface like every other
object (no bespoke write path to drift). Each artifact endpoint
serves ONE generated file so consumers fetch only what they need.

@consumers
  - grpcbridge/renode_twin/fpga build script (fetches artifacts)
  - hwfpga.selftest_fpga (function-level via fpga_verilog)
"""

from objectTreeDecorators import treeObject, treeObjectInit

from hwfpga.fpga_verilog import (
    get_map, map_registers, render_c_defines, render_core,
    render_sim_main, render_sim_top, render_testbench,
)


class FpgaRegisterMapAPI(treeObject):
    """Catalogue + generated-artifact downloads for register maps."""

    @treeObjectInit
    def __init__(self, polServer):
        self.polServer = polServer
        self.apiName = '/api/hw/registermaps'
        if polServer is not None:
            add = polServer.falconServer.add_route
            add('/api/hw/registermaps', self, suffix='catalogue')
            add('/api/hw/registermaps/{map_name}/{artifact}', self,
                suffix='artifact')

    def on_get_catalogue(self, request, response):
        tables = getattr(self.manager, 'objectTables', None) or {}
        maps = []
        for row in (tables.get('RegisterMapDefinition')
                    or {}).values():
            registers = map_registers(self.manager,
                                      getattr(row, 'name', ''))
            maps.append({
                'name': getattr(row, 'name', ''),
                'baseAddress': hex(int(getattr(row, 'base_address',
                                               0))),
                'bus': getattr(row, 'bus', ''),
                'description': getattr(row, 'description', ''),
                'registers': [{
                    'register': getattr(r, 'register', ''),
                    'offset': hex(int(getattr(r, 'offset', 0))),
                    'access': getattr(r, 'access', ''),
                    'resetValue': hex(int(getattr(r, 'reset_value',
                                                  0))),
                    'description': getattr(r, 'description', ''),
                    'editKnob': f'/RegisterDefinition (CRUDE PUT '
                                f'polariId={getattr(r, "id", "?")})',
                } for r in registers],
                'artifacts': [
                    f'/api/hw/registermaps/{row.name}/{a}'
                    for a in ('verilog', 'sim-top', 'sim-harness',
                              'c-defines', 'testbench')],
            })
        maps.sort(key=lambda m: m['name'])
        response.media = {'ok': True, 'maps': maps}

    def on_get_artifact(self, request, response, map_name, artifact):
        map_row = get_map(self.manager, map_name)
        if map_row is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f'no register map "{map_name}"'}
            return
        registers = map_registers(self.manager, map_name)
        renderers = {
            'verilog': lambda: render_core(map_row, registers),
            'sim-top': lambda: render_sim_top(registers),
            'sim-harness': render_sim_main,
            'c-defines': lambda: render_c_defines(map_row, registers),
            'testbench': lambda: render_testbench(registers),
        }
        renderer = renderers.get(artifact)
        if renderer is None:
            response.status = '404 Not Found'
            response.media = {'ok': False,
                              'error': f'unknown artifact "{artifact}"'
                                       f' ({" | ".join(renderers)})'}
            return
        response.content_type = 'text/plain; charset=utf-8'
        response.text = renderer()

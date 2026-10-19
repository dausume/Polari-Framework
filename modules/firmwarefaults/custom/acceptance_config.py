"""
@module firmwarefaults.custom.acceptance_config

fsc-6: A PURPOSE'S OWN ACCEPTANCE SCENARIO RUN ON ANOTHER BUILT CONFIG. A Purpose is proven for a config only by a passed ScenarioRun of THAT config's own firmware (cmod.custom.fsc_link). So the
four Purposes of uno-light-mission each need a run per config - this is the one mechanism for it, not eight copied Scenarios: `acceptance.run(scenario, variant=V)` runs the SAME Scenario (its
own name, its own steps, its own negative controls) on V's build and stores the ScenarioRun with `variant` = V (the config it ran), so `fsc_link` finds it.

  boot (initialization-acceptance)                          board.custom.light_boot_twin.prove(mode, V)      - boot_session is on both wire classes
  button / observe / command (light-from-button-, ensure-polari-observes-hardware-state-, light-from-polari-acceptance)
                                                            V's app is `light` -> board.custom.light_twin.prove(which, mode, V)
                                                            V's app is `button_clock` -> board.custom.light_variant_twin.prove(which, V, mode)   (ButtonClockState stand-ins, named there)

Refused (route 'refused', so the run is stored `inapplicable` and proves nothing) when V is not a built config of the Mission or the Scenario is not a Purpose's own (`fsc_link.proof_config_refusal`),
or when no runner exists for the Scenario. The server's Purpose door applies the same refusal to a pushed run.
"""


def refusal(sc, variant, manager=None):
    """'' when `variant` may run Scenario `sc`, else why not."""
    from cmod.custom import fsc_link
    from firmwarefaults.custom import acceptance as ACC
    why = fsc_link.proof_config_refusal(variant, sc['name'], manager)
    if why:
        return why
    if sc['name'] not in ACC.BOOT_PROOFS and sc['capability'] not in ACC.LIGHT_WHICH:
        return 'no per-config runner is written for scenario %r' % sc['name']
    return ''


def prove(sc, variant, run_mode):
    """-> the {'ok', 'route', 'why', ...} result of the SAME check the Scenario runs on its own variant, on `variant`'s build."""
    from board.custom import variants as V
    from firmwarefaults.custom import acceptance as ACC
    if sc['name'] in ACC.BOOT_PROOFS:
        from board.custom import light_boot_twin as LB
        return LB.prove(run_mode, variant)
    which = ACC.LIGHT_WHICH[sc['capability']]
    app = (V.find(variant) or {}).get('app')
    if app == 'light':
        from board.custom import light_twin as LT
        return LT.prove(which, run_mode, variant)
    if app == 'button_clock':
        from board.custom import light_variant_twin as LVT
        return LVT.prove(which, variant, run_mode)
    return {'ok': False, 'route': 'refused', 'why': 'no light runner for a config of app %r' % app}

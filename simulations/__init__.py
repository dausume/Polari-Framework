"""
@cross-cutting
@module simulations
@tags @xc:render-shared, @xc:bindings

Simulation infrastructure — sample classes + the SimulationDefinition
config tie-in + a storage predictor. The runtime engine (which iterates
a step-function no-code solution) is planned but not yet wired; today's
demos use precomputed reference trajectories so visualization works
while the engine is built.

@see /OVERLAP_MAP.md
"""

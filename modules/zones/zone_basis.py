"""
@module zones.zone_basis
@tags @xc:bindings

AR zone capture rows (AR_ZONE_CAPTURE_PLAN.md arz-1, Dustin
2026-07-17): capture a 3D area by placing points in AR — 3 points
minimum for a volume, more to make a shape in the air — then size and
place simulated objects inside it.

  SiteDefinition     — the HOUSE/lot: a named collection of zones
                       captured room-by-room, so "how much fits in the
                       whole house" needs no global coordinate frame.
  ZoneDefinition     — one captured zone. capture_mode 'prism' (ground
                       polygon + height) or 'hull' (free points, the
                       shape-in-the-air). scale_correction is the
                       calibration knob (reference points across a
                       KNOWN real length).
  ZonePoint          — one placed point, METERS in zone-local space
                       (WebXR local-floor is metric, y up). kind
                       'ground' | 'height' | 'free' | 'reference'.
  ZoneEstimateRecord — persisted estimate verdicts so a zone's history
                       stays inspectable.

@consumers
  - polariServer.defClassList (auto-CRUDE + persistence)
  - zones.zones_api / zone_geometry / zone_packing
@see /AR_ZONE_CAPTURE_PLAN.md
"""
# sap-2c INDEX (design §7): the classes live one-per-file under objects/zone/;
# this file re-exports them (imports keep working) and holds what they share.
# The original imports stay: names this file imported were re-exported implicitly.

from objectTreeDecorators import treeObject, treeObjectInit
from simulations.seed_data import SEED_SIMULATION_DEFINITIONS  # noqa: E402

from zones.objects.zone._shared import CAPTURE_MODES, POINT_KINDS, SEED_SITES, SEED_ZONES, SEED_ZONE_POINTS, ZONE_ROLES, ZONE_STATUSES, _demo_hull_points, _demo_planar_points, _demo_prism_points  # noqa: F401
from zones.objects.zone.SiteDefinition import SiteDefinition  # noqa: F401
from zones.objects.zone.ZoneDefinition import ZoneDefinition  # noqa: F401
from zones.objects.zone.ZonePoint import ZonePoint  # noqa: F401
from zones.objects.zone.ZoneEstimateRecord import ZoneEstimateRecord  # noqa: F401

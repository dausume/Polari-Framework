"""
@module cicd.custom — the cicd module's logic, one concern per file.

cicd_validate  the ONE rule set (device.sh's validation, in python)
cicd_stages    CI_ISLE_STAGES ⇄ PipelineStage rows
cicd_auth      who may change a setting (a person, ADMIN_ROLES) vs who may mirror a run in (a posting-only token)
cicd_ingest    the five mirror kinds and everything the door refuses
cicd_rows      reading the tables back (the answer GET /api/cicd gives the pipeline)
"""

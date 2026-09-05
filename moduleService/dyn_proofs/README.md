# dyn-1..9 proof harnesses

The scripts that PROVED each phase of DYNAMIC_MODULES_PLAN.md, kept
so the claims are re-runnable rather than remembered.

Run each inside a one-off container, with the repo mounted **AT
/app** (the image carries its own /app/modules copy on PYTHONPATH —
mounting elsewhere leaves module code importable and silently
invalidates any absence test):

    docker run --rm -u 1000:1000 -e HOME=/tmp -e PROOF_REPO=/app \
      -v $PWD:/app -v $PWD/moduleService/dyn_proofs/<script>:/p.py:ro \
      -w /app --entrypoint python3 prf-backend:staging /p.py

- parity_dump.py  — dyn-1 boot parity (routes/classes/uris/tables);
                    run against a `dev` worktree and the branch, diff.
- dyn2_proof.py   — live admission (404 -> 200, no restart)
- dyn3_proof.py   — put-away -> 410 -> re-admit restores rows
- dyn4_proof.py   — a module ABSENT at boot, fetched + admitted
- dyn5_proof.py   — baseline boot + dependency-closure admission
- dyn68_proof.py  — app modulePlan suggestion -> act -> ready
- dyn7_proof.py   — module-move plan + local half
- dyn9.py         — devices + consumed-vs-available ledger
                    (in-process falcon TestClient)

⚠ dyn4_proof.py DELETES modules/gears from the mounted repo and lets
the fetch restore it. If it dies mid-run, restore from git.

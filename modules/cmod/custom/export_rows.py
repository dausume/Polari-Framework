"""
@module cmod.custom.export_rows

The FirmwareExport rows a page shows (GET /api/firmware/exports), narrowed in plain ways:

  solution=<name>       only that firmware solution's exports
  latest_per_form=1     the NEWEST export of each form (per solution when no solution is named), so an older bundle
                        built before the last change does not sit beside today's. Everything older stays a row on the
                        server (the bare door still lists it); it is only left out of this view.

Pure (rows in, rows out) so the selftest needs no server.
"""


def narrow(rows, solution='', latest_per_form=False):
    """rows: dicts with solution / form / created_at. Newest first on the way out (created_at is an ISO string, name breaks ties)."""
    out = [r for r in rows if not solution or r.get('solution') == solution]
    out.sort(key=lambda r: (r.get('created_at') or '', r.get('name') or ''), reverse=True)
    if latest_per_form:
        seen, keep = set(), []
        for r in out:   # newest first: the first of each (solution, form) wins
            k = (r.get('solution') or '', r.get('form') or '')
            if k not in seen:
                seen.add(k)
                keep.append(r)
        out = keep
    return out

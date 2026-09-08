"""
The test-build entrypoint — "full test suite" is a BUILD TARGET:

    python3 -m testing.custom.run_matrix [--category substrate]
                                  [--check <name> ...] [--list]
                                  [--results-dir DIR] [--live-url URL]
                                  [--timeout SECONDS]

Runs the capability matrix (Dockerfile.test lineage; docker
compose -f docker-compose.test.yml up), emits
test-results/test-report.yaml, and exits 0 iff blocking_green —
the pipeline gates on either signal, they always agree.
"""

import argparse
import sys

from testing.check_catalog import catalog_checks
from testing.custom.matrix_runner import exit_code_for, run_matrix


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='python3 -m testing.custom.run_matrix',
        description='Run the accountability capability matrix.')
    parser.add_argument('--category',
                        help='only checks in this category')
    parser.add_argument('--check', action='append', dest='checks',
                        help='only this named check (repeatable)')
    parser.add_argument('--list', action='store_true',
                        help='print the catalog and exit')
    parser.add_argument('--results-dir',
                        help='where test-report.yaml lands '
                             '(default test-results/)')
    parser.add_argument('--live-url',
                        help='live server for live:* checks '
                             '(default POLARI_SMOKE_BASE_URL)')
    parser.add_argument('--timeout', type=int,
                        help='per-check timeout seconds')
    args = parser.parse_args(argv)

    if args.list:
        for entry in catalog_checks():
            print(f"{entry['category']:10s} "
                  f"{entry['criticality']:13s} {entry['name']}")
        return 0

    record = run_matrix(category=args.category, names=args.checks,
                        results_dir=args.results_dir,
                        live_base_url=args.live_url,
                        timeout=args.timeout)
    return exit_code_for(record)


if __name__ == '__main__':
    sys.exit(main())

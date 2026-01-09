#!/usr/bin/env python3
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
Test runner for Polari Framework
Runs all test suites and reports results
"""

import sys
import os
import unittest

# Ensure tests directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main test runner"""
    print("\n" + "="*80)
    print(" "*20 + "POLARI FRAMEWORK TEST SUITE")
    print("="*80 + "\n")

    # Discover and run all tests
    loader = unittest.TestLoader()
    start_dir = os.path.join(os.path.dirname(__file__), 'tests')

    # Check if tests directory exists
    if not os.path.exists(start_dir):
        print(f"ERROR: Tests directory not found: {start_dir}")
        print("Creating tests directory...")
        os.makedirs(start_dir, exist_ok=True)

    suite = loader.discover(start_dir, pattern='test*.py')

    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*80)
    print(" "*30 + "FINAL RESULTS")
    print("="*80)
    print(f"Total Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n" + " "*30 + "✓ ALL TESTS PASSED")
    else:
        print("\n" + " "*30 + "✗ SOME TESTS FAILED")

    print("="*80 + "\n")

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())

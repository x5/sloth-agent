#!/usr/bin/env python3
"""Bisection script to find which test creates unwanted files/state.

Usage:
    uv run python find_polluter.py <file_or_dir_to_check> <test_pattern>

Examples:
    uv run python find_polluter.py ".git" "tests/**/test_*.py"
    uv run python find_polluter.py "output/results.json" "tests/test_pipeline.py"
"""

import glob
import os
import subprocess
import sys


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <file_to_check> <test_pattern>")
        print(f'Example: {sys.argv[0]} ".git" "tests/**/test_*.py"')
        sys.exit(1)

    pollution_check = sys.argv[1]
    test_pattern = sys.argv[2]

    print(f"Searching for test that creates: {pollution_check}")
    print(f"Test pattern: {test_pattern}")
    print()

    # Get list of test files
    test_files = sorted(glob.glob(test_pattern, recursive=True))
    total = len(test_files)

    if total == 0:
        print(f"No test files found matching: {test_pattern}")
        sys.exit(1)

    print(f"Found {total} test files")
    print()

    for i, test_file in enumerate(test_files, 1):
        # Skip if pollution already exists
        if os.path.exists(pollution_check):
            print(f"  Pollution already exists before test {i}/{total}")
            print(f"   Skipping: {test_file}")
            # Clean up if possible
            if os.path.isdir(pollution_check) and not os.path.islink(pollution_check):
                import shutil
                shutil.rmtree(pollution_check, ignore_errors=True)
            else:
                os.remove(pollution_check)
            continue

        print(f"[{i}/{total}] Testing: {test_file}")

        # Run the test
        subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-q"],
            capture_output=True,
        )

        # Check if pollution appeared
        if os.path.exists(pollution_check):
            print()
            print("FOUND POLLUTER!")
            print(f"   Test: {test_file}")
            print(f"   Created: {pollution_check}")
            print()
            print("Pollution details:")
            if os.path.isdir(pollution_check):
                for root, dirs, files in os.walk(pollution_check):
                    for f in files:
                        print(f"  {os.path.join(root, f)}")
            else:
                print(f"  {os.path.abspath(pollution_check)}")
            print()
            print("To investigate:")
            print(f"  uv run pytest {test_file}    # Run just this test")
            print(f"  cat {test_file}         # Review test code")
            sys.exit(1)

    print()
    print("No polluter found - all tests clean!")
    sys.exit(0)


if __name__ == "__main__":
    main()

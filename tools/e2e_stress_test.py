#!/usr/bin/env python3
"""Stress test runner for CodeBot E2E scripts.

Usage: python3 tools/e2e_stress_test.py --iterations 200 --concurrency 50 --registry-runs 5

This script runs many instances of the build->preview E2E test in parallel
to simulate concurrent users, and runs a small number of registry-persistence
tests sequentially (they restart the backend and are not safe to run concurrently).
"""
import argparse
import subprocess
import sys
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_cmd(cmd, timeout=None):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:
        return 124, str(e)


def _wait_for_backend(host='127.0.0.1', port=8080, timeout=30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def run_concurrent_build_tests(total, concurrency, batch_size=10, max_retries=2):
    print(f"Starting {total} build-preview tests with concurrency={concurrency} (batch_size={batch_size})")
    successes = 0
    failures = 0
    start = time.time()

    remaining = total
    # Run in batches to avoid large surges
    while remaining > 0:
        this_batch = min(batch_size, remaining)
        print(f"Launching batch of {this_batch} build tests...")
        with ThreadPoolExecutor(max_workers=min(this_batch, concurrency)) as ex:
            futures = [ex.submit(run_cmd, "python3 tools/e2e_build_preview_test.py", 120) for _ in range(this_batch)]
            for fut in as_completed(futures):
                code, out = fut.result()
                if code == 0 and "E2E PASSED" in out:
                    successes += 1
                else:
                    # Retry a small number of times for transient failures
                    retried = False
                    for r in range(max_retries):
                        time.sleep(0.5)
                        code2, out2 = run_cmd("python3 tools/e2e_build_preview_test.py", 120)
                        if code2 == 0 and "E2E PASSED" in out2:
                            successes += 1
                            retried = True
                            break
                    if not retried:
                        failures += 1
                        print("--- FAILED TASK OUTPUT ---")
                        print(out)
                        print("--- END FAILED OUTPUT ---")

        remaining -= this_batch

        # Small pause between batches to allow the backend to stabilize
        time.sleep(0.6)

    elapsed = time.time() - start
    print(f"Build tests done: success={successes} failed={failures} elapsed={elapsed:.1f}s")
    return successes, failures


def run_registry_tests(runs):
    print(f"Running {runs} registry-persistence tests sequentially (these restart the backend)")
    successes = 0
    failures = 0
    for i in range(runs):
        # Ensure backend is accepting connections before starting the test
        ok = _wait_for_backend(timeout=20.0)
        if not ok:
            print("Backend not reachable before registry test, aborting run")
            return successes, runs - successes

        code, out = run_cmd("python3 tools/e2e_registry_persistence_test.py", 180)
        if code == 0 and "E2E registry persistence PASSED" in out:
            successes += 1
        else:
            failures += 1
            print(f"Registry test {i+1} failed: return={code}")
            print(out)
        # Wait for backend to come back after restart
        time.sleep(1.0)
        if not _wait_for_backend(timeout=30.0):
            print("Backend did not come back up after registry test")
            return successes, runs - successes

    print(f"Registry tests done: success={successes} failed={failures}")
    return successes, failures


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--iterations", type=int, default=200)
    p.add_argument("--concurrency", type=int, default=50)
    p.add_argument("--registry-runs", type=int, default=5)
    args = p.parse_args()

    # Run registry tests first (they restart backend and are disruptive)
    r_succ, r_fail = run_registry_tests(args.registry_runs)

    # Then run the bulk concurrent build-preview tests
    b_succ, b_fail = run_concurrent_build_tests(args.iterations, args.concurrency)

    total = args.registry_runs + args.iterations
    total_success = r_succ + b_succ
    total_fail = r_fail + b_fail

    print("\nStress test summary")
    print(f"Total runs: {total}")
    print(f"Successes: {total_success}")
    print(f"Failures: {total_fail}")

    if total_fail > 0:
        sys.exit(2)
    print("ALL STRESS TESTS PASSED")


if __name__ == '__main__':
    main()

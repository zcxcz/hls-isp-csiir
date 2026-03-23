#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP-CSIIR Intermediate Stage Data Comparison Tool

This script compares intermediate stage data between Python golden model
and HLS model outputs to verify HLS implementation correctness.

Usage:
    python compare_intermediate.py [test_name]

Author: rtl-verf
Date: 2026-03-23
Version: v1.0
"""

import os
import sys
import numpy as np
from typing import Tuple, Dict, List
from dataclasses import dataclass


@dataclass
class ComparisonResult:
    """Result of comparing a single data field."""
    field_name: str
    total_count: int
    match_count: int
    max_diff: int
    mean_diff: float
    mismatch_samples: List[Tuple[int, int, int, int]]  # (row, col, expected, actual)


def load_stage_data(filename: str, stage: int) -> Dict[Tuple[int, int], Dict]:
    """Load intermediate stage data from file."""
    data = {}

    if not os.path.exists(filename):
        print(f"Warning: File not found: {filename}")
        return data

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            row = int(parts[0])
            col = int(parts[1])
            values = [int(v) for v in parts[2:]]

            if stage == 1:
                data[(row, col)] = {
                    'grad': values[0],
                    'win_size': values[1],
                    'grad_h': values[2],
                    'grad_v': values[3]
                }
            elif stage == 2:
                data[(row, col)] = {
                    'avg0_c': values[0], 'avg0_u': values[1], 'avg0_d': values[2],
                    'avg0_l': values[3], 'avg0_r': values[4],
                    'avg1_c': values[5], 'avg1_u': values[6], 'avg1_d': values[7],
                    'avg1_l': values[8], 'avg1_r': values[9]
                }
            elif stage == 3:
                data[(row, col)] = {
                    'blend0_grad': values[0],
                    'blend1_grad': values[1]
                }
            elif stage == 4:
                data[(row, col)] = {
                    'input': values[0],
                    'output': values[1]
                }

    return data


def compare_field(expected: Dict, actual: Dict, field: str,
                  tolerance: int = 0) -> ComparisonResult:
    """Compare a single field between expected and actual data."""
    match_count = 0
    total_count = 0
    max_diff = 0
    sum_diff = 0
    mismatches = []

    for key in expected:
        if key not in actual:
            continue

        total_count += 1
        exp_val = expected[key][field]
        act_val = actual[key][field]
        diff = abs(exp_val - act_val)

        if diff <= tolerance:
            match_count += 1
        else:
            if len(mismatches) < 10:  # Keep first 10 mismatches
                mismatches.append((key[0], key[1], exp_val, act_val))

        max_diff = max(max_diff, diff)
        sum_diff += diff

    mean_diff = sum_diff / total_count if total_count > 0 else 0

    return ComparisonResult(
        field_name=field,
        total_count=total_count,
        match_count=match_count,
        max_diff=max_diff,
        mean_diff=mean_diff,
        mismatch_samples=mismatches
    )


def print_comparison_result(result: ComparisonResult, tolerance: int):
    """Print comparison result in a formatted way."""
    match_rate = 100.0 * result.match_count / result.total_count if result.total_count > 0 else 0

    status = "PASS" if match_rate == 100.0 else "WARN" if match_rate >= 99.0 else "FAIL"

    print(f"    {result.field_name}: {result.match_count}/{result.total_count} "
          f"({match_rate:.2f}%) [{status}]")
    print(f"      Max diff: {result.max_diff}, Mean diff: {result.mean_diff:.2f}")

    if result.mismatch_samples:
        print(f"      Sample mismatches (first 5):")
        for row, col, exp, act in result.mismatch_samples[:5]:
            print(f"        ({row},{col}): expected={exp}, actual={act}")


def compare_stage1(test_name: str, intermediate_dir: str) -> bool:
    """Compare Stage 1 intermediate data."""
    print("\n  === Stage 1: Gradient Computation ===")

    python_file = os.path.join(intermediate_dir, 'python', f'{test_name}_stage1.txt')
    hls_file = os.path.join(intermediate_dir, 'hls', f'{test_name}_stage1.txt')

    expected = load_stage_data(python_file, 1)
    actual = load_stage_data(hls_file, 1)

    if not expected or not actual:
        print("    ERROR: Missing data files")
        return False

    all_pass = True
    for field in ['grad', 'win_size', 'grad_h', 'grad_v']:
        tolerance = 1 if field != 'win_size' else 0  # win_size must match exactly
        result = compare_field(expected, actual, field, tolerance)
        print_comparison_result(result, tolerance)

        match_rate = 100.0 * result.match_count / result.total_count
        if match_rate < 99.0:
            all_pass = False

    return all_pass


def compare_stage2(test_name: str, intermediate_dir: str) -> bool:
    """Compare Stage 2 intermediate data."""
    print("\n  === Stage 2: Multi-scale Directional Average ===")

    python_file = os.path.join(intermediate_dir, 'python', f'{test_name}_stage2.txt')
    hls_file = os.path.join(intermediate_dir, 'hls', f'{test_name}_stage2.txt')

    expected = load_stage_data(python_file, 2)
    actual = load_stage_data(hls_file, 2)

    if not expected or not actual:
        print("    ERROR: Missing data files")
        return False

    all_pass = True
    for field in ['avg0_c', 'avg0_u', 'avg0_d', 'avg0_l', 'avg0_r',
                   'avg1_c', 'avg1_u', 'avg1_d', 'avg1_l', 'avg1_r']:
        tolerance = 2  # Allow small rounding differences
        result = compare_field(expected, actual, field, tolerance)
        print_comparison_result(result, tolerance)

        match_rate = 100.0 * result.match_count / result.total_count
        if match_rate < 95.0:  # More tolerance for division approximations
            all_pass = False

    return all_pass


def compare_stage3(test_name: str, intermediate_dir: str) -> bool:
    """Compare Stage 3 intermediate data."""
    print("\n  === Stage 3: Gradient-weighted Directional Fusion ===")

    python_file = os.path.join(intermediate_dir, 'python', f'{test_name}_stage3.txt')
    hls_file = os.path.join(intermediate_dir, 'hls', f'{test_name}_stage3.txt')

    expected = load_stage_data(python_file, 3)
    actual = load_stage_data(hls_file, 3)

    if not expected or not actual:
        print("    ERROR: Missing data files")
        return False

    all_pass = True
    for field in ['blend0_grad', 'blend1_grad']:
        tolerance = 3  # Allow more tolerance for NR division
        result = compare_field(expected, actual, field, tolerance)
        print_comparison_result(result, tolerance)

        match_rate = 100.0 * result.match_count / result.total_count
        if match_rate < 95.0:
            all_pass = False

    return all_pass


def compare_output(test_name: str, intermediate_dir: str) -> bool:
    """Compare final output data."""
    print("\n  === Final Output ===")

    python_file = os.path.join(intermediate_dir, 'python', f'{test_name}_output.txt')
    hls_file = os.path.join(intermediate_dir, 'hls', f'{test_name}_output.txt')

    expected = load_stage_data(python_file, 4)
    actual = load_stage_data(hls_file, 4)

    if not expected or not actual:
        print("    ERROR: Missing data files")
        return False

    # Compare input pixels first (should match exactly)
    input_result = compare_field(expected, actual, 'input', tolerance=0)
    print(f"    Input pixels: {input_result.match_count}/{input_result.total_count} match")

    # Compare output pixels
    output_result = compare_field(expected, actual, 'output', tolerance=2)
    print_comparison_result(output_result, tolerance=2)

    match_rate = 100.0 * output_result.match_count / output_result.total_count
    return match_rate >= 95.0


def run_comparison(test_name: str, intermediate_dir: str) -> Dict[str, bool]:
    """Run complete comparison for a test case."""
    print(f"\n{'='*60}")
    print(f"Comparing: {test_name}")
    print(f"{'='*60}")

    results = {
        'stage1': compare_stage1(test_name, intermediate_dir),
        'stage2': compare_stage2(test_name, intermediate_dir),
        'stage3': compare_stage3(test_name, intermediate_dir),
        'output': compare_output(test_name, intermediate_dir)
    }

    # Summary
    print(f"\n  Summary:")
    all_pass = True
    for stage, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"    {stage}: {status}")
        if not passed:
            all_pass = False

    results['all_pass'] = all_pass
    return results


def main():
    print("=" * 60)
    print("ISP-CSIIR Intermediate Stage Data Comparison Tool")
    print("=" * 60)

    # Directory setup
    script_dir = os.path.dirname(os.path.abspath(__file__))
    intermediate_dir = os.path.join(os.path.dirname(script_dir), 'intermediate')

    # Test names to compare
    if len(sys.argv) > 1:
        test_names = sys.argv[1:]
    else:
        test_names = [
            'flat',
            'gradient_h',
            'gradient_v',
            'checkerboard',
            'edge',
            'center_peak',
            'edge_small'
        ]

    # Run comparisons
    all_results = {}
    for test_name in test_names:
        all_results[test_name] = run_comparison(test_name, intermediate_dir)

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results.values() if r.get('all_pass', False))

    print(f"\nTotal tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")

    print("\nDetailed Results:")
    print("-" * 40)
    print(f"{'Test Name':<20} {'Stage1':<8} {'Stage2':<8} {'Stage3':<8} {'Output':<8}")
    print("-" * 40)

    for test_name, results in all_results.items():
        s1 = "PASS" if results.get('stage1', False) else "FAIL"
        s2 = "PASS" if results.get('stage2', False) else "FAIL"
        s3 = "PASS" if results.get('stage3', False) else "FAIL"
        out = "PASS" if results.get('output', False) else "FAIL"
        print(f"{test_name:<20} {s1:<8} {s2:<8} {s3:<8} {out:<8}")

    print("-" * 40)

    if passed_tests == total_tests:
        print("\n*** ALL TESTS PASSED ***")
        return 0
    else:
        print(f"\n*** {total_tests - passed_tests} TEST(S) FAILED ***")
        return 1


if __name__ == "__main__":
    sys.exit(main())
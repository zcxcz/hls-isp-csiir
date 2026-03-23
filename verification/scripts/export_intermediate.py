#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP-CSIIR Intermediate Stage Data Exporter

This script processes test vectors and exports intermediate stage data
for HLS verification comparison.

Output files per test vector:
  - intermediate/python/{name}_stage1.txt: grad, win_size, grad_h, grad_v per pixel
  - intermediate/python/{name}_stage2.txt: avg0_c/u/d/l/r, avg1_c/u/d/l/r per pixel
  - intermediate/python/{name}_stage3.txt: blend0_grad, blend1_grad per pixel
  - intermediate/python/{name}_output.txt: final output per pixel

Author: rtl-verf
Date: 2026-03-23
Version: v1.0
"""

import os
import sys
import numpy as np
from typing import List

# Import from compute_expected
from compute_expected import (
    process_image, load_input_image,
    Stage1Result, Stage2Result, Stage3Result, ProcessingResult,
    INV_TABLE, div_by_5, div_by_lookup, div_by_nr,
    AVG_FACTOR_2x2, AVG_FACTOR_3x3, AVG_FACTOR_4x4, AVG_FACTOR_5x5,
    MASK_U, MASK_D, MASK_L, MASK_R,
    MAX_PIXEL
)


def save_stage1_data(results: List[ProcessingResult], filename: str, width: int = 64):
    """Save Stage 1 intermediate data."""
    with open(filename, 'w') as f:
        # Header
        f.write("# Stage 1: Gradient Computation Results\n")
        f.write("# Format: row col grad win_size grad_h grad_v\n")
        f.write("# grad: combined gradient (U12)\n")
        f.write("# win_size: window size (U6)\n")
        f.write("# grad_h: horizontal gradient (S14)\n")
        f.write("# grad_v: vertical gradient (S14)\n")

        idx = 0
        for r in results:
            row = idx // width
            col = idx % width
            f.write(f"{row} {col} {r.stage1.grad} {r.stage1.win_size} "
                    f"{r.stage1.grad_h} {r.stage1.grad_v}\n")
            idx += 1
    print(f"  Saved Stage 1 data: {filename}")


def save_stage2_data(results: List[ProcessingResult], filename: str, width: int = 64):
    """Save Stage 2 intermediate data."""
    with open(filename, 'w') as f:
        # Header
        f.write("# Stage 2: Multi-scale Directional Average Results\n")
        f.write("# Format: row col avg0_c avg0_u avg0_d avg0_l avg0_r "
                "avg1_c avg1_u avg1_d avg1_l avg1_r\n")
        f.write("# avg values: Q11 signed [-512, 511]\n")

        idx = 0
        for r in results:
            row = idx // width
            col = idx % width
            f.write(f"{row} {col} "
                    f"{r.stage2.avg0_c} {r.stage2.avg0_u} {r.stage2.avg0_d} "
                    f"{r.stage2.avg0_l} {r.stage2.avg0_r} "
                    f"{r.stage2.avg1_c} {r.stage2.avg1_u} {r.stage2.avg1_d} "
                    f"{r.stage2.avg1_l} {r.stage2.avg1_r}\n")
            idx += 1
    print(f"  Saved Stage 2 data: {filename}")


def save_stage3_data(results: List[ProcessingResult], filename: str, width: int = 64):
    """Save Stage 3 intermediate data."""
    with open(filename, 'w') as f:
        # Header
        f.write("# Stage 3: Gradient-weighted Directional Fusion Results\n")
        f.write("# Format: row col blend0_grad blend1_grad\n")
        f.write("# blend values: Q11 signed [-512, 511]\n")

        idx = 0
        for r in results:
            row = idx // width
            col = idx % width
            f.write(f"{row} {col} {r.stage3.blend0_grad} {r.stage3.blend1_grad}\n")
            idx += 1
    print(f"  Saved Stage 3 data: {filename}")


def save_output_data(results: List[ProcessingResult], filename: str, width: int = 64):
    """Save final output data."""
    with open(filename, 'w') as f:
        # Header
        f.write("# Stage 4: Final Output Results\n")
        f.write("# Format: row col input_pixel output_pixel\n")
        f.write("# pixels: U10 unsigned [0, 1023]\n")

        idx = 0
        for r in results:
            row = idx // width
            col = idx % width
            f.write(f"{row} {col} {r.input_pixel} {r.output_pixel}\n")
            idx += 1
    print(f"  Saved Output data: {filename}")


def process_and_export(input_file: str, name: str, width: int, height: int,
                       win_thresh: List[int] = None,
                       grad_clip: List[int] = None,
                       blend_ratio: List[int] = None):
    """Process a test vector and export all intermediate data."""

    # Default parameters (matching HLS testbench)
    if win_thresh is None:
        win_thresh = [16, 24, 32, 40]
    if grad_clip is None:
        grad_clip = [15, 23, 31, 39]
    if blend_ratio is None:
        blend_ratio = [32, 32, 32, 32]

    # Load input
    input_image = load_input_image(input_file, width, height)

    # Process with intermediate results
    output_image, results = process_image(
        input_image, win_thresh, grad_clip, blend_ratio
    )

    # Determine base path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    intermediate_dir = os.path.join(os.path.dirname(script_dir), 'intermediate', 'python')
    os.makedirs(intermediate_dir, exist_ok=True)

    # Save all intermediate data
    save_stage1_data(results, os.path.join(intermediate_dir, f"{name}_stage1.txt"), width)
    save_stage2_data(results, os.path.join(intermediate_dir, f"{name}_stage2.txt"), width)
    save_stage3_data(results, os.path.join(intermediate_dir, f"{name}_stage3.txt"), width)
    save_output_data(results, os.path.join(intermediate_dir, f"{name}_output.txt"), width)

    # Statistics
    print(f"  Input range: [{input_image.min()}, {input_image.max()}]")
    print(f"  Output range: [{output_image.min()}, {output_image.max()}]")

    return results


if __name__ == "__main__":
    print("=" * 60)
    print("ISP-CSIIR Intermediate Stage Data Exporter")
    print("=" * 60)

    # Directory setup
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
    TEST_VECTORS_DIR = os.path.join(PROJECT_DIR, 'verification', 'test_vectors')

    # Process test vectors (focus on key patterns for verification)
    # Using actual test vector names from generate_test_vectors.py
    test_configs = [
        ("flat", 64, 64),
        ("flat_small", 16, 16),
        ("gradient_h", 64, 64),
        ("gradient_v", 64, 64),
        ("checkerboard", 64, 64),
        ("checkerboard_small", 16, 16),
        ("edge", 64, 64),
        ("edge_small", 16, 16),
        ("center_peak", 64, 64),
        ("corner", 64, 64),
        ("boundary", 64, 64),
        ("random", 64, 64),
    ]

    for name, width, height in test_configs:
        input_file = os.path.join(TEST_VECTORS_DIR, f"input_{name}.txt")

        if os.path.exists(input_file):
            print(f"\nProcessing: {name}")
            process_and_export(input_file, name, width, height)
        else:
            print(f"Skipping: {name} (input not found)")

    print("\n" + "=" * 60)
    print("Intermediate data export complete!")
    print("Files saved to: verification/intermediate/python/")
    print("=" * 60)
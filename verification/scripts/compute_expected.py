#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP-CSIIR Golden Reference Model

This script computes expected outputs for the ISP-CSIIR HLS module.
It implements the same algorithm as the HLS code for verification purposes.

Author: rtl-verf
Date: 2026-03-23
Version: v1.0
"""

import os
import sys
import numpy as np
from typing import Tuple, List, Dict
from dataclasses import dataclass

# ============================================================
# Constants
# ============================================================
DATA_WIDTH = 10
MAX_PIXEL = 1023
MIN_PIXEL = 0
RATIO_SCALE = 64
MAX_WIDTH = 8192
WIN_SIZE = 5

# Sobel filter coefficients
SOBEL_X = np.array([
    [ 1,  1,  1,  1,  1],
    [ 0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0],
    [ 0,  0,  0,  0,  0],
    [-1, -1, -1, -1, -1]
], dtype=np.int32)

SOBEL_Y = np.array([
    [ 1,  0,  0,  0, -1],
    [ 1,  0,  0,  0, -1],
    [ 1,  0,  0,  0, -1],
    [ 1,  0,  0,  0, -1],
    [ 1,  0,  0,  0, -1]
], dtype=np.int32)

# Average factor kernels
AVG_FACTOR_2x2 = np.array([
    [0, 0, 0, 0, 0],
    [0, 1, 2, 1, 0],
    [0, 2, 4, 2, 0],
    [0, 1, 2, 1, 0],
    [0, 0, 0, 0, 0]
], dtype=np.int32)

AVG_FACTOR_3x3 = np.array([
    [0, 0, 0, 0, 0],
    [0, 1, 1, 1, 0],
    [0, 1, 1, 1, 0],
    [0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0]
], dtype=np.int32)

AVG_FACTOR_4x4 = np.array([
    [1, 1, 2, 1, 1],
    [1, 2, 4, 2, 1],
    [2, 4, 8, 4, 2],
    [1, 2, 4, 2, 1],
    [1, 1, 2, 1, 1]
], dtype=np.int32)

AVG_FACTOR_5x5 = np.array([
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1]
], dtype=np.int32)

# Direction masks
MASK_U = np.array([
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0]
], dtype=np.int32)

MASK_D = np.array([
    [0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1]
], dtype=np.int32)

MASK_L = np.array([
    [1, 1, 1, 0, 0],
    [1, 1, 1, 0, 0],
    [1, 1, 1, 0, 0],
    [1, 1, 1, 0, 0],
    [1, 1, 1, 0, 0]
], dtype=np.int32)

MASK_R = np.array([
    [0, 0, 1, 1, 1],
    [0, 0, 1, 1, 1],
    [0, 0, 1, 1, 1],
    [0, 0, 1, 1, 1],
    [0, 0, 1, 1, 1]
], dtype=np.int32)


# ============================================================
# Data Classes for Intermediate Results
# ============================================================
@dataclass
class Stage1Result:
    """Stage 1 output: Gradient computation"""
    grad: int
    win_size: int
    grad_h: int
    grad_v: int


@dataclass
class Stage2Result:
    """Stage 2 output: Directional averages"""
    avg0_c: int
    avg0_u: int
    avg0_d: int
    avg0_l: int
    avg0_r: int
    avg1_c: int
    avg1_u: int
    avg1_d: int
    avg1_l: int
    avg1_r: int


@dataclass
class Stage3Result:
    """Stage 3 output: Gradient-weighted fusion"""
    blend0_grad: int
    blend1_grad: int


@dataclass
class ProcessingResult:
    """Complete processing result for a pixel"""
    input_pixel: int
    output_pixel: int
    stage1: Stage1Result
    stage2: Stage2Result
    stage3: Stage3Result


# ============================================================
# Division Utilities (Matching HLS Implementation)
# ============================================================
def div_by_5(x: int) -> int:
    """Division by 5 using multiply approximation: x/5 ≈ (x*205)>>10"""
    return (x * 205) >> 10


def div_by_64(x: int) -> int:
    """Division by 64 using right shift: x/64 = x>>6"""
    if x >= 0:
        return x >> 6
    else:
        return -((-x) >> 6)


# Reciprocal lookup table
INV_TABLE = [0] + [int(65536 / d) for d in range(1, 65)]


def div_by_lookup(numerator: int, denominator: int) -> int:
    """Division using lookup table for reciprocal."""
    if denominator == 0:
        return 0

    is_negative = numerator < 0
    abs_num = abs(numerator)
    inv = INV_TABLE[min(denominator, 64)]
    result = (abs_num * inv) >> 16

    return -result if is_negative else result


def initial_reciprocal(denominator: int) -> int:
    """Initial reciprocal estimate for Newton-Raphson."""
    if denominator <= 64:
        return INV_TABLE[denominator]
    # Shift-based approximation
    msb_pos = denominator.bit_length() - 1
    return 1 << (16 - msb_pos)


def div_by_nr(numerator: int, denominator: int) -> int:
    """Newton-Raphson division."""
    if denominator == 0 or numerator == 0:
        return 0

    is_negative = numerator < 0
    abs_num = abs(numerator)

    # Initial estimate
    x0 = initial_reciprocal(denominator)

    # First NR iteration: x1 = x0 * (2 - D * x0)
    prod0 = denominator * x0
    two_minus = (2 << 16) - prod0
    x1 = (x0 * two_minus) >> 16

    # Second NR iteration
    prod1 = denominator * x1
    two_minus1 = (2 << 16) - prod1
    x2 = (x1 * two_minus1) >> 16

    # Compute quotient
    result = (abs_num * x2) >> 16

    # Saturate
    if result > 511:
        result = 511

    return -result if is_negative else result


# ============================================================
# Image Processing Functions
# ============================================================
def get_pixel_with_boundary(image: np.ndarray, row: int, col: int) -> int:
    """Get pixel with boundary replication."""
    height, width = image.shape

    # Clamp coordinates
    r = max(0, min(row, height - 1))
    c = max(0, min(col, width - 1))

    return int(image[r, c])


def get_5x5_window(image: np.ndarray, row: int, col: int) -> np.ndarray:
    """Extract 5x5 window with boundary handling."""
    window = np.zeros((5, 5), dtype=np.int32)

    for i in range(5):
        for j in range(5):
            window[i, j] = get_pixel_with_boundary(image, row + i - 2, col + j - 2)

    return window


def convert_to_signed(window: np.ndarray) -> np.ndarray:
    """Convert unsigned pixel values to signed (centered at 512)."""
    return window.astype(np.int32) - 512


# ============================================================
# Stage 1: Gradient Computation
# ============================================================
def compute_gradient(window: np.ndarray, grad_clip: List[int]) -> Stage1Result:
    """
    Stage 1: Compute gradient and window size.

    Args:
        window: 5x5 pixel window (unsigned)
        grad_clip: Gradient clip thresholds [4 values]

    Returns:
        Stage1Result with gradient values
    """
    # Compute Sobel gradients
    grad_h = int(np.sum(window[0, :]) - np.sum(window[4, :]))
    grad_v = int(np.sum(window[:, 0]) - np.sum(window[:, 4]))

    # Compute combined gradient
    grad_h_abs = abs(grad_h)
    grad_v_abs = abs(grad_v)

    grad_h_div5 = div_by_5(grad_h_abs)
    grad_v_div5 = div_by_5(grad_v_abs)

    grad = grad_h_div5 + grad_v_div5

    # Determine window size based on gradient
    if grad <= grad_clip[0]:
        win_size = 16
    elif grad <= grad_clip[1]:
        win_size = 23
    elif grad <= grad_clip[2]:
        win_size = 31
    elif grad <= grad_clip[3]:
        win_size = 39
    else:
        win_size = 40

    return Stage1Result(grad=grad, win_size=win_size, grad_h=grad_h, grad_v=grad_v)


# ============================================================
# Stage 2: Multi-scale Directional Average
# ============================================================
def compute_directional_average(window_s11: np.ndarray, factor: np.ndarray,
                                mask: np.ndarray) -> Tuple[int, int]:
    """Compute weighted average with direction mask."""
    masked_factor = factor * mask
    weighted_sum = np.sum(window_s11 * masked_factor)
    sum_factor = np.sum(masked_factor)

    if sum_factor == 0:
        return 0, 0

    avg_value = div_by_lookup(int(weighted_sum), int(sum_factor))
    return avg_value, sum_factor


def compute_averages(window_s11: np.ndarray, win_size: int,
                     win_thresh: List[int]) -> Stage2Result:
    """
    Stage 2: Compute multi-scale directional averages.

    Args:
        window_s11: 5x5 signed pixel window
        win_size: Window size from Stage 1
        win_thresh: Window size thresholds [4 values]

    Returns:
        Stage2Result with directional averages
    """
    # Select kernels based on window size
    if win_size < win_thresh[0]:
        avg0_factor = np.zeros((5, 5), dtype=np.int32)
        avg1_factor = AVG_FACTOR_2x2
    elif win_size < win_thresh[1]:
        avg0_factor = AVG_FACTOR_2x2
        avg1_factor = AVG_FACTOR_3x3
    elif win_size < win_thresh[2]:
        avg0_factor = AVG_FACTOR_3x3
        avg1_factor = AVG_FACTOR_4x4
    elif win_size < win_thresh[3]:
        avg0_factor = AVG_FACTOR_4x4
        avg1_factor = AVG_FACTOR_5x5
    else:
        avg0_factor = AVG_FACTOR_5x5
        avg1_factor = np.zeros((5, 5), dtype=np.int32)

    # Compute avg0 values
    avg0_c, _ = compute_directional_average(window_s11, avg0_factor, np.ones((5, 5)))
    avg0_u, _ = compute_directional_average(window_s11, avg0_factor, MASK_U)
    avg0_d, _ = compute_directional_average(window_s11, avg0_factor, MASK_D)
    avg0_l, _ = compute_directional_average(window_s11, avg0_factor, MASK_L)
    avg0_r, _ = compute_directional_average(window_s11, avg0_factor, MASK_R)

    # Compute avg1 values
    avg1_c, _ = compute_directional_average(window_s11, avg1_factor, np.ones((5, 5)))
    avg1_u, _ = compute_directional_average(window_s11, avg1_factor, MASK_U)
    avg1_d, _ = compute_directional_average(window_s11, avg1_factor, MASK_D)
    avg1_l, _ = compute_directional_average(window_s11, avg1_factor, MASK_L)
    avg1_r, _ = compute_directional_average(window_s11, avg1_factor, MASK_R)

    return Stage2Result(
        avg0_c=avg0_c, avg0_u=avg0_u, avg0_d=avg0_d, avg0_l=avg0_l, avg0_r=avg0_r,
        avg1_c=avg1_c, avg1_u=avg1_u, avg1_d=avg1_d, avg1_l=avg1_l, avg1_r=avg1_r
    )


# ============================================================
# Stage 3: Gradient-weighted Directional Fusion
# ============================================================
def compute_blend_gradient(avg_values: List[int], grad_values: List[int]) -> int:
    """Compute gradient-weighted blend."""
    grad_sum = sum(grad_values)

    if grad_sum == 0:
        # Equal weight average
        return sum(avg_values) // 5

    # Gradient-weighted average
    weighted_sum = sum(a * g for a, g in zip(avg_values, grad_values))
    return div_by_nr(weighted_sum, grad_sum)


def compute_fusion(s2_result: Stage2Result, grad_center: int) -> Stage3Result:
    """
    Stage 3: Compute gradient-weighted fusion.

    For simplicity, uses center gradient for all directions.
    In full implementation, would use neighboring gradients.

    Args:
        s2_result: Stage 2 output
        grad_center: Center gradient value

    Returns:
        Stage3Result with blend gradients
    """
    # Use center gradient for all directions (simplified)
    grad_values = [grad_center] * 5

    # Compute blend0 (smaller kernel)
    avg0_values = [s2_result.avg0_c, s2_result.avg0_u, s2_result.avg0_d,
                   s2_result.avg0_l, s2_result.avg0_r]
    blend0_grad = compute_blend_gradient(avg0_values, grad_values)

    # Compute blend1 (larger kernel)
    avg1_values = [s2_result.avg1_c, s2_result.avg1_u, s2_result.avg1_d,
                   s2_result.avg1_l, s2_result.avg1_r]
    blend1_grad = compute_blend_gradient(avg1_values, grad_values)

    return Stage3Result(blend0_grad=blend0_grad, blend1_grad=blend1_grad)


# ============================================================
# Stage 4: IIR Filtering and Blend Output
# ============================================================
def compute_output(s3_result: Stage3Result, s2_result: Stage2Result,
                   win_size: int, win_thresh: List[int],
                   blend_ratio: List[int], edge_protect: int,
                   window_s11: np.ndarray) -> int:
    """
    Stage 4: Compute final output.

    Args:
        s3_result: Stage 3 output
        s2_result: Stage 2 output
        win_size: Window size
        win_thresh: Window thresholds
        blend_ratio: Blend ratios
        edge_protect: Edge protection coefficient
        window_s11: 5x5 signed pixel window

    Returns:
        Final output pixel value
    """
    # Determine blend ratio index
    ratio_idx = min((win_size >> 3) - 2, 3)
    ratio_idx = max(0, ratio_idx)
    ratio = blend_ratio[ratio_idx]

    # Horizontal blend
    def horizontal_blend(blend_grad: int, avg_u: int, ratio: int) -> int:
        numerator = ratio * blend_grad + (RATIO_SCALE - ratio) * avg_u
        return numerator >> 6

    blend0_hor = horizontal_blend(s3_result.blend0_grad, s2_result.avg0_u, ratio)
    blend1_hor = horizontal_blend(s3_result.blend1_grad, s2_result.avg1_u, ratio)

    # Simplified window blend (using center pixel)
    center_pixel = window_s11[2, 2]

    # Simple blending based on window size
    if win_size < win_thresh[0]:
        blend_uv = blend0_hor
    elif win_size >= win_thresh[3]:
        blend_uv = blend1_hor
    else:
        # Interpolate
        win_remain = win_size & 0x7
        blend_uv = (blend0_hor * win_remain + blend1_hor * (8 - win_remain)) >> 3

    # Convert to unsigned and clip
    output_signed = blend_uv + 512
    output = max(0, min(output_signed, MAX_PIXEL))

    return output


# ============================================================
# Main Processing Pipeline
# ============================================================
def process_image(image: np.ndarray,
                  win_thresh: List[int] = None,
                  grad_clip: List[int] = None,
                  blend_ratio: List[int] = None,
                  edge_protect: int = 32) -> Tuple[np.ndarray, List[ProcessingResult]]:
    """
    Process entire image through ISP-CSIIR pipeline.

    Args:
        image: Input image (2D numpy array)
        win_thresh: Window size thresholds
        grad_clip: Gradient clip thresholds
        blend_ratio: Blend ratios
        edge_protect: Edge protection coefficient

    Returns:
        Tuple of (output_image, list of per-pixel results)
    """
    # Default parameters
    if win_thresh is None:
        win_thresh = [16, 24, 32, 40]
    if grad_clip is None:
        grad_clip = [15, 23, 31, 39]
    if blend_ratio is None:
        blend_ratio = [32, 32, 32, 32]

    height, width = image.shape
    output_image = np.zeros((height, width), dtype=np.uint16)
    results = []

    for row in range(height):
        for col in range(width):
            # Get 5x5 window
            window = get_5x5_window(image, row, col)
            window_s11 = convert_to_signed(window)

            # Stage 1: Gradient computation
            s1_result = compute_gradient(window, grad_clip)

            # Stage 2: Directional averages
            s2_result = compute_averages(window_s11, s1_result.win_size, win_thresh)

            # Stage 3: Gradient-weighted fusion
            s3_result = compute_fusion(s2_result, s1_result.grad)

            # Stage 4: Output
            output = compute_output(
                s3_result, s2_result, s1_result.win_size,
                win_thresh, blend_ratio, edge_protect, window_s11
            )

            output_image[row, col] = output

            # Store result for debugging
            result = ProcessingResult(
                input_pixel=int(image[row, col]),
                output_pixel=output,
                stage1=s1_result,
                stage2=s2_result,
                stage3=s3_result
            )
            results.append(result)

    return output_image, results


# ============================================================
# File I/O and Main
# ============================================================
def save_expected_output(image: np.ndarray, filename: str):
    """Save expected output image to file."""
    height, width = image.shape
    with open(filename, 'w') as f:
        for row in range(height):
            for col in range(width):
                f.write(f"{image[row, col]}\n")
    print(f"Saved expected output: {filename}")


def load_input_image(filename: str, width: int, height: int) -> np.ndarray:
    """Load input image from file."""
    image = np.zeros((height, width), dtype=np.uint16)
    with open(filename, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines):
            if i >= width * height:
                break
            row = i // width
            col = i % width
            image[row, col] = int(line.strip())
    return image


def process_test_vector(input_file: str, output_file: str,
                        width: int, height: int,
                        win_thresh: List[int] = None,
                        grad_clip: List[int] = None,
                        blend_ratio: List[int] = None):
    """Process a single test vector file."""
    # Load input
    input_image = load_input_image(input_file, width, height)

    # Process
    output_image, _ = process_image(
        input_image, win_thresh, grad_clip, blend_ratio
    )

    # Save output
    save_expected_output(output_image, output_file)

    # Print statistics
    print(f"  Input range: [{input_image.min()}, {input_image.max()}]")
    print(f"  Output range: [{output_image.min()}, {output_image.max()}]")
    print(f"  Output mean: {output_image.mean():.2f}")


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("ISP-CSIIR Golden Reference Model")
    print("=" * 50)

    # Directory setup
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
    TEST_VECTORS_DIR = os.path.join(PROJECT_DIR, 'verification', 'test_vectors')
    EXPECTED_DIR = os.path.join(PROJECT_DIR, 'verification', 'expected_outputs')

    os.makedirs(EXPECTED_DIR, exist_ok=True)

    # Process default test vectors
    test_configs = [
        ("flat", 64, 64),
        ("gradient_h", 64, 64),
        ("gradient_v", 64, 64),
        ("checkerboard", 64, 64),
        ("edge", 64, 64),
        ("center_peak", 64, 64),
        ("random", 64, 64),
        ("corner", 64, 64),
        ("boundary", 64, 64),
        ("extreme", 64, 64),
        ("edge_small", 16, 16),
    ]

    for name, width, height in test_configs:
        input_file = os.path.join(TEST_VECTORS_DIR, f"input_{name}.txt")
        output_file = os.path.join(EXPECTED_DIR, f"expected_{name}.txt")

        if os.path.exists(input_file):
            print(f"\nProcessing: {name}")
            process_test_vector(input_file, output_file, width, height)
        else:
            print(f"Skipping: {name} (input not found)")

    print("\nDone!")
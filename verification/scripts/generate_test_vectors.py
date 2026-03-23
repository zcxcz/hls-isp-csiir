#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP-CSIIR HLS Test Vector Generator

This script generates test vectors for the ISP-CSIIR HLS module verification.

Author: rtl-verf
Date: 2026-03-23
Version: v1.0
"""

import os
import sys
import numpy as np
from typing import Tuple, List

# ============================================================
# Constants
# ============================================================
DATA_WIDTH = 10
MAX_PIXEL = 1023
MIN_PIXEL = 0
DEFAULT_WIDTH = 64
DEFAULT_HEIGHT = 64

# Output directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
TEST_VECTORS_DIR = os.path.join(PROJECT_DIR, 'verification', 'test_vectors')
EXPECTED_OUTPUTS_DIR = os.path.join(PROJECT_DIR, 'verification', 'expected_outputs')


# ============================================================
# Test Image Generators
# ============================================================
def generate_flat_image(width: int, height: int, value: int = 512) -> np.ndarray:
    """Generate a flat image with constant pixel value."""
    return np.full((height, width), value, dtype=np.uint16)


def generate_horizontal_gradient(width: int, height: int) -> np.ndarray:
    """Generate an image with horizontal gradient."""
    image = np.zeros((height, width), dtype=np.uint16)
    for col in range(width):
        value = int(col * MAX_PIXEL / (width - 1))
        image[:, col] = value
    return image


def generate_vertical_gradient(width: int, height: int) -> np.ndarray:
    """Generate an image with vertical gradient."""
    image = np.zeros((height, width), dtype=np.uint16)
    for row in range(height):
        value = int(row * MAX_PIXEL / (height - 1))
        image[row, :] = value
    return image


def generate_diagonal_gradient(width: int, height: int) -> np.ndarray:
    """Generate an image with diagonal gradient."""
    image = np.zeros((height, width), dtype=np.uint16)
    for row in range(height):
        for col in range(width):
            value = int((row + col) * MAX_PIXEL / (width + height - 2))
            image[row, col] = min(value, MAX_PIXEL)
    return image


def generate_checkerboard(width: int, height: int, block_size: int = 8,
                          value1: int = 200, value2: int = 800) -> np.ndarray:
    """Generate a checkerboard pattern."""
    image = np.zeros((height, width), dtype=np.uint16)
    for row in range(height):
        for col in range(width):
            block_row = row // block_size
            block_col = col // block_size
            if (block_row + block_col) % 2 == 0:
                image[row, col] = value1
            else:
                image[row, col] = value2
    return image


def generate_edge_pattern(width: int, height: int) -> np.ndarray:
    """Generate an image with distinct edges."""
    image = np.full((height, width), 512, dtype=np.uint16)
    # Vertical edge
    mid_col = width // 2
    image[:, mid_col] = 900
    # Horizontal edge
    mid_row = height // 2
    image[mid_row, :] = 100
    return image


def generate_center_peak(width: int, height: int) -> np.ndarray:
    """Generate an image with center peak."""
    image = np.zeros((height, width), dtype=np.uint16)
    center_x = width // 2
    center_y = height // 2
    max_dist = center_x + center_y

    for row in range(height):
        for col in range(width):
            dist = abs(col - center_x) + abs(row - center_y)
            value = int(MAX_PIXEL * (max_dist - dist) / max_dist)
            image[row, col] = max(0, min(value, MAX_PIXEL))
    return image


def generate_random_noise(width: int, height: int, seed: int = 42) -> np.ndarray:
    """Generate a random noise image."""
    np.random.seed(seed)
    return np.random.randint(0, MAX_PIXEL + 1, (height, width), dtype=np.uint16)


def generate_corner_test(width: int, height: int) -> np.ndarray:
    """Generate an image to test corner handling."""
    image = np.full((height, width), 256, dtype=np.uint16)
    # Mark corners with distinct values
    image[0, 0] = 100        # Top-left
    image[0, width-1] = 200  # Top-right
    image[height-1, 0] = 300 # Bottom-left
    image[height-1, width-1] = 400 # Bottom-right
    return image


def generate_boundary_test(width: int, height: int) -> np.ndarray:
    """Generate an image to test boundary handling."""
    image = np.full((height, width), 400, dtype=np.uint16)
    # First row
    image[0, :] = 100
    # Last row
    image[height-1, :] = 200
    # First column
    image[:, 0] = 300
    # Last column
    image[:, width-1] = 500
    return image


def generate_extreme_values(width: int, height: int) -> np.ndarray:
    """Generate an image with extreme values (0 and 1023)."""
    image = np.zeros((height, width), dtype=np.uint16)
    for row in range(height):
        for col in range(width):
            if (row + col) % 2 == 0:
                image[row, col] = 0
            else:
                image[row, col] = MAX_PIXEL
    return image


# ============================================================
# File I/O Functions
# ============================================================
def save_image_to_file(image: np.ndarray, filename: str):
    """Save image to text file (one pixel per line)."""
    height, width = image.shape
    with open(filename, 'w') as f:
        for row in range(height):
            for col in range(width):
                f.write(f"{image[row, col]}\n")
    print(f"Saved: {filename} ({width}x{height})")


def save_image_as_matrix(image: np.ndarray, filename: str):
    """Save image as matrix format (space-separated)."""
    height, width = image.shape
    with open(filename, 'w') as f:
        for row in range(height):
            line = ' '.join(str(image[row, col]) for col in range(width))
            f.write(line + '\n')
    print(f"Saved: {filename} ({width}x{height})")


def load_image_from_file(filename: str, width: int, height: int) -> np.ndarray:
    """Load image from text file."""
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


# ============================================================
# Configuration Generator
# ============================================================
def generate_config_file(filename: str, width: int, height: int,
                         win_thresh: List[int] = None,
                         grad_clip: List[int] = None,
                         blend_ratio: List[int] = None,
                         edge_protect: int = 32):
    """Generate configuration file for test."""
    if win_thresh is None:
        win_thresh = [16, 24, 32, 40]
    if grad_clip is None:
        grad_clip = [15, 23, 31, 39]
    if blend_ratio is None:
        blend_ratio = [32, 32, 32, 32]

    with open(filename, 'w') as f:
        f.write(f"# ISP-CSIIR Test Configuration\n")
        f.write(f"IMG_WIDTH={width}\n")
        f.write(f"IMG_HEIGHT={height}\n")
        f.write(f"WIN_THRESH_0={win_thresh[0]}\n")
        f.write(f"WIN_THRESH_1={win_thresh[1]}\n")
        f.write(f"WIN_THRESH_2={win_thresh[2]}\n")
        f.write(f"WIN_THRESH_3={win_thresh[3]}\n")
        f.write(f"GRAD_CLIP_0={grad_clip[0]}\n")
        f.write(f"GRAD_CLIP_1={grad_clip[1]}\n")
        f.write(f"GRAD_CLIP_2={grad_clip[2]}\n")
        f.write(f"GRAD_CLIP_3={grad_clip[3]}\n")
        f.write(f"BLEND_RATIO_0={blend_ratio[0]}\n")
        f.write(f"BLEND_RATIO_1={blend_ratio[1]}\n")
        f.write(f"BLEND_RATIO_2={blend_ratio[2]}\n")
        f.write(f"BLEND_RATIO_3={blend_ratio[3]}\n")
        f.write(f"EDGE_PROTECT={edge_protect}\n")
    print(f"Saved config: {filename}")


# ============================================================
# Main Test Vector Generation
# ============================================================
def generate_all_test_vectors():
    """Generate all test vectors for verification."""

    # Ensure output directories exist
    os.makedirs(TEST_VECTORS_DIR, exist_ok=True)
    os.makedirs(EXPECTED_OUTPUTS_DIR, exist_ok=True)

    # Test image definitions
    test_images = [
        ("flat", generate_flat_image, {}),
        ("gradient_h", generate_horizontal_gradient, {}),
        ("gradient_v", generate_vertical_gradient, {}),
        ("gradient_d", generate_diagonal_gradient, {}),
        ("checkerboard", generate_checkerboard, {"block_size": 8, "value1": 200, "value2": 800}),
        ("edge", generate_edge_pattern, {}),
        ("center_peak", generate_center_peak, {}),
        ("random", generate_random_noise, {"seed": 42}),
        ("corner", generate_corner_test, {}),
        ("boundary", generate_boundary_test, {}),
        ("extreme", generate_extreme_values, {}),
    ]

    # Additional sizes for boundary testing
    sizes = [
        (DEFAULT_WIDTH, DEFAULT_HEIGHT, ""),
        (16, 16, "_small"),
        (128, 128, "_medium"),
    ]

    for name, generator, kwargs in test_images:
        for width, height, suffix in sizes:
            if suffix and name in ["random", "center_peak"]:
                # Skip some combinations to reduce test count
                continue

            # Generate image
            image = generator(width, height, **kwargs)

            # Save as linear file (for HLS TB)
            filename = os.path.join(TEST_VECTORS_DIR, f"input_{name}{suffix}.txt")
            save_image_to_file(image, filename)

            # Also save as matrix for visualization
            filename_matrix = os.path.join(TEST_VECTORS_DIR, f"input_{name}{suffix}_matrix.txt")
            save_image_as_matrix(image, filename_matrix)

    # Generate configuration files
    generate_config_file(
        os.path.join(TEST_VECTORS_DIR, "config_default.txt"),
        DEFAULT_WIDTH, DEFAULT_HEIGHT
    )
    generate_config_file(
        os.path.join(TEST_VECTORS_DIR, "config_small.txt"),
        16, 16
    )
    generate_config_file(
        os.path.join(TEST_VECTORS_DIR, "config_aggressive.txt"),
        DEFAULT_WIDTH, DEFAULT_HEIGHT,
        win_thresh=[10, 20, 30, 40],
        grad_clip=[10, 20, 30, 40],
        blend_ratio=[48, 48, 48, 48]
    )

    print(f"\nTest vectors generated in: {TEST_VECTORS_DIR}")


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("ISP-CSIIR Test Vector Generator")
    print("=" * 50)

    generate_all_test_vectors()

    print("\nDone!")
// ============================================================
// ISP-CSIIR HLS Type Definitions
// ============================================================
// Project: ISP-CSIIR HLS Module
// Version: v1.0
// Date: 2026-03-23
// Description: Fixed-point type definitions for ISP-CSIIR module
// ============================================================

#ifndef ISP_CSIIR_TYPES_H
#define ISP_CSIIR_TYPES_H

// Include compatibility headers for standalone compilation
// Use local headers when not in Vitis HLS environment
#include "include/ap_int.h"
#include "include/ap_fixed.h"
#include "include/hls_stream.h"
#include "include/hls_pragmas.h"

// ============================================================
// Constants
// ============================================================
const int MAX_WIDTH = 8192;
const int MAX_HEIGHT = 8192;
const int WIN_SIZE = 5;
const int RATIO_SCALE = 64;
const int GRAD_DIV_SHIFT = 10;
const int GRAD_DIV_MUL = 205;
const int EDGE_PROTECT_DEFAULT = 32;

// ============================================================
// Input/Output Types
// ============================================================
// 10-bit unsigned pixel for input/output
typedef ap_uint<10> pixel_u10_t;

// 11-bit signed pixel for internal computation
typedef ap_int<11> pixel_s11_t;

// AXI-Stream data type with side channels
struct axis_pixel_t {
    pixel_u10_t data;
    ap_uint<1> last;
    ap_uint<1> user;  // SOF indicator
};

// ============================================================
// Stage 1 Types: Gradient Computation
// ============================================================
// Horizontal/Vertical gradient: Q14.0, range [-5115, 5115]
typedef ap_int<14> grad_hv_t;

// Gradient absolute value: UQ13.0, range [0, 5115]
typedef ap_uint<13> grad_abs_t;

// Combined gradient: UQ12.0, range [0, 2046]
typedef ap_uint<12> grad_t;

// Window size: UQ6.0, range [16, 40]
typedef ap_uint<6> win_size_t;

// Row sum for Sobel: UQ13.0, range [0, 5115]
typedef ap_uint<13> row_sum_t;

// ============================================================
// Stage 2 Types: Multi-scale Directional Average
// ============================================================
// Average factor: UQ4.0, range [0, 8]
typedef ap_uint<4> avg_factor_t;

// Weighted sum: Q16.0, range [-32704, 32704]
typedef ap_int<16> weighted_sum_t;

// Sum factor (denominator): UQ7.0, range [1, 64]
typedef ap_uint<7> sum_factor_t;

// Average value: Q11.0, range [-512, 511]
typedef ap_int<11> avg_value_t;

// ============================================================
// Stage 3 Types: Gradient-weighted Directional Fusion
// ============================================================
// Gradient sum: UQ14.0, range [0, 10230]
typedef ap_uint<14> grad_sum_t;

// Average weighted product sum: Q23.0
typedef ap_int<23> avg_weighted_t;

// Blend gradient result: Q11.0, range [-512, 511]
typedef ap_int<11> blend_grad_t;

// ============================================================
// Stage 4 Types: IIR Filtering and Blend Output
// ============================================================
// Blend ratio: UQ7.0, range [0, 64]
typedef ap_uint<7> ratio_t;

// Horizontal blend numerator: Q16.0
typedef ap_int<16> blend_hor_num_t;

// Window blend result: Q17.0
typedef ap_int<17> blend_win_t;

// Window remainder: UQ4.0, range [0, 7]
typedef ap_uint<4> win_remain_t;

// ============================================================
// Configuration Structure
// ============================================================
struct config_t {
    ap_uint<16> img_width;      // Image width
    ap_uint<16> img_height;     // Image height
    ap_uint<8>  win_thresh[4];  // Window size thresholds [16, 24, 32, 40]
    ap_uint<8>  grad_clip[4];   // Gradient clip thresholds [15, 23, 31, 39]
    ap_uint<8>  blend_ratio[4]; // IIR blend ratios [32, 32, 32, 32]
    ap_uint<8>  edge_protect;   // Edge protection coefficient
};

// ============================================================
// Internal Stream Data Types
// ============================================================
// Stage 1 output
struct stage1_out_t {
    grad_t grad;
    win_size_t win_size;
    pixel_s11_t src_5x5[5][5];
};

// Stage 2 output
struct stage2_out_t {
    avg_value_t avg0_c, avg0_u, avg0_d, avg0_l, avg0_r;
    avg_value_t avg1_c, avg1_u, avg1_d, avg1_l, avg1_r;
    win_size_t win_size;
    pixel_s11_t src_5x5[5][5];
    grad_t grad_center;  // Center gradient for reference
};

// Stage 3 output
struct stage3_out_t {
    blend_grad_t blend0_grad;
    blend_grad_t blend1_grad;
    avg_value_t avg0_u;
    avg_value_t avg1_u;
    win_size_t win_size;
    pixel_s11_t src_5x5[5][5];
};

// ============================================================
// Sobel Filter Coefficients
// ============================================================
const ap_int<2> SOBEL_X[5][5] = {
    { 1,  1,  1,  1,  1},
    { 0,  0,  0,  0,  0},
    { 0,  0,  0,  0,  0},
    { 0,  0,  0,  0,  0},
    {-1, -1, -1, -1, -1}
};

const ap_int<2> SOBEL_Y[5][5] = {
    { 1,  0,  0,  0, -1},
    { 1,  0,  0,  0, -1},
    { 1,  0,  0,  0, -1},
    { 1,  0,  0,  0, -1},
    { 1,  0,  0,  0, -1}
};

// ============================================================
// Average Factor Kernels
// ============================================================
// 2x2 kernel (9 non-zero elements)
const avg_factor_t AVG_FACTOR_2x2[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 1, 2, 1, 0},
    {0, 2, 4, 2, 0},
    {0, 1, 2, 1, 0},
    {0, 0, 0, 0, 0}
};

// 3x3 kernel (9 non-zero elements)
const avg_factor_t AVG_FACTOR_3x3[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 1, 1, 1, 0},
    {0, 1, 1, 1, 0},
    {0, 1, 1, 1, 0},
    {0, 0, 0, 0, 0}
};

// 4x4 kernel (25 non-zero elements)
const avg_factor_t AVG_FACTOR_4x4[5][5] = {
    {1, 1, 2, 1, 1},
    {1, 2, 4, 2, 1},
    {2, 4, 8, 4, 2},
    {1, 2, 4, 2, 1},
    {1, 1, 2, 1, 1}
};

// 5x5 kernel (25 elements, all 1)
const avg_factor_t AVG_FACTOR_5x5[5][5] = {
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1}
};

// ============================================================
// Direction Masks
// ============================================================
// Up mask
const ap_uint<1> MASK_U[5][5] = {
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0}
};

// Down mask
const ap_uint<1> MASK_D[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1}
};

// Left mask
const ap_uint<1> MASK_L[5][5] = {
    {1, 1, 1, 0, 0},
    {1, 1, 1, 0, 0},
    {1, 1, 1, 0, 0},
    {1, 1, 1, 0, 0},
    {1, 1, 1, 0, 0}
};

// Right mask
const ap_uint<1> MASK_R[5][5] = {
    {0, 0, 1, 1, 1},
    {0, 0, 1, 1, 1},
    {0, 0, 1, 1, 1},
    {0, 0, 1, 1, 1},
    {0, 0, 1, 1, 1}
};

// ============================================================
// Blend Factor Kernels for Stage 4
// ============================================================
// 2x2 horizontal blend factor
const avg_factor_t BLEND_FACTOR_2x2_H[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0},
    {0, 1, 1, 1, 0},
    {0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0}
};

// 2x2 vertical blend factor
const avg_factor_t BLEND_FACTOR_2x2_V[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 0, 1, 0, 0},
    {0, 0, 1, 0, 0},
    {0, 0, 1, 0, 0},
    {0, 0, 0, 0, 0}
};

// 2x2 blend factor
const avg_factor_t BLEND_FACTOR_2x2[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 1, 2, 1, 0},
    {0, 2, 4, 2, 0},
    {0, 1, 2, 1, 0},
    {0, 0, 0, 0, 0}
};

// 3x3 blend factor
const avg_factor_t BLEND_FACTOR_3x3[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 1, 1, 1, 0},
    {0, 1, 1, 1, 0},
    {0, 1, 1, 1, 0},
    {0, 0, 0, 0, 0}
};

// 4x4 blend factor
const avg_factor_t BLEND_FACTOR_4x4[5][5] = {
    {1, 2, 2, 2, 1},
    {2, 4, 4, 4, 2},
    {2, 4, 4, 4, 2},
    {2, 4, 4, 4, 2},
    {1, 2, 2, 2, 1}
};

// 5x5 blend factor
const avg_factor_t BLEND_FACTOR_5x5[5][5] = {
    {4, 4, 4, 4, 4},
    {4, 4, 4, 4, 4},
    {4, 4, 4, 4, 4},
    {4, 4, 4, 4, 4},
    {4, 4, 4, 4, 4}
};

// ============================================================
// Default Configuration Values
// ============================================================
const ap_uint<8> DEFAULT_WIN_THRESH[4] = {16, 24, 32, 40};
const ap_uint<8> DEFAULT_GRAD_CLIP[4] = {15, 23, 31, 39};
const ap_uint<8> DEFAULT_BLEND_RATIO[4] = {32, 32, 32, 32};

#endif // ISP_CSIIR_TYPES_H
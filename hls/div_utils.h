// ============================================================
// ISP-CSIIR Division Utilities Header
// ============================================================
// Project: ISP-CSIIR HLS Module
// Version: v1.0
// Date: 2026-03-23
// Description: Division utility functions for HLS implementation
//   - Constant division (multiply approximation, shift)
//   - Variable division (lookup table, Newton-Raphson)
// ============================================================

#ifndef DIV_UTILS_H
#define DIV_UTILS_H

#include "isp_csiir_types.h"

// ============================================================
// Division by 5 (Multiply Approximation)
// ============================================================
// x / 5 ≈ (x * 205) >> 10
// Maximum error: < 0.1%
// ============================================================
ap_uint<11> div_by_5(ap_uint<13> grad_abs);

// ============================================================
// Division by 64 (Right Shift)
// ============================================================
// x / 64 = x >> 6 (exact)
// ============================================================
ap_int<11> div_by_64(ap_int<17> numerator);

// ============================================================
// Division by Lookup Table (for small denominators)
// ============================================================
// Pre-computed reciprocal table for denominators [1, 64]
// inv_table[d] = 2^16 / d
// ============================================================
ap_int<11> div_by_lookup(ap_int<16> numerator, ap_uint<7> denominator);

// ============================================================
// Newton-Raphson Division (for large denominators)
// ============================================================
// Uses 2 iterations of Newton-Raphson method
// x_0 = initial_guess(1/D)
// x_1 = x_0 * (2 - D * x_0)
// x_2 = x_1 * (2 - D * x_1)
// Q = N * x_2
// ============================================================
ap_int<11> div_by_nr(ap_int<23> numerator, ap_uint<14> denominator);

// ============================================================
// Initial Reciprocal Estimate for NR Division
// ============================================================
// Uses lookup table for initial estimate
// Returns 2^16 / D with approximate accuracy
// ============================================================
ap_uint<16> initial_reciprocal(ap_uint<14> denominator);

// ============================================================
// Reciprocal Lookup Table (65 entries for indices 0-64)
// ============================================================
extern const ap_uint<16> INV_TABLE[65];

// ============================================================
// Specific sum_factor reciprocal table
// ============================================================
// Only 8 possible values: 1, 6, 9, 10, 15, 16, 25, 40, 64
// ============================================================
extern const ap_uint<16> SUM_FACTOR_INV_TABLE[65];

#endif // DIV_UTILS_H
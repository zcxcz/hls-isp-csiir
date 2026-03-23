// ============================================================
// ISP-CSIIR Division Utilities Implementation
// ============================================================
// Project: ISP-CSIIR HLS Module
// Version: v1.0
// Date: 2026-03-23
// ============================================================

#include "div_utils.h"

// ============================================================
// Reciprocal Lookup Table (65 entries)
// inv_table[d] = floor(65536 / d) for d in [1, 64]
// ============================================================
const ap_uint<16> INV_TABLE[65] = {
    0,      // 0: unused
    65536,  // 1: 65536
    32768,  // 2: 32768
    21845,  // 3: 21845
    16384,  // 4: 16384
    13107,  // 5: 13107
    10923,  // 6: 10923
    9362,   // 7: 9362
    8192,   // 8: 8192
    7282,   // 9: 7282
    6554,   // 10: 6554
    5958,   // 11: 5958
    5461,   // 12: 5461
    5041,   // 13: 5041
    4681,   // 14: 4681
    4369,   // 15: 4369
    4096,   // 16: 4096
    3855,   // 17: 3855
    3641,   // 18: 3641
    3449,   // 19: 3449
    3277,   // 20: 3277
    3121,   // 21: 3121
    2979,   // 22: 2979
    2849,   // 23: 2849
    2731,   // 24: 2731
    2621,   // 25: 2621
    2521,   // 26: 2521
    2427,   // 27: 2427
    2341,   // 28: 2341
    2256,   // 29: 2256
    2185,   // 30: 2185
    2115,   // 31: 2115
    2048,   // 32: 2048
    1986,   // 33: 1986
    1928,   // 34: 1928
    1872,   // 35: 1872
    1820,   // 36: 1820
    1771,   // 37: 1771
    1725,   // 38: 1725
    1680,   // 39: 1680
    1638,   // 40: 1638
    1598,   // 41: 1598
    1560,   // 42: 1560
    1524,   // 43: 1524
    1490,   // 44: 1490
    1457,   // 45: 1457
    1425,   // 46: 1425
    1395,   // 47: 1395
    1365,   // 48: 1365
    1337,   // 49: 1337
    1311,   // 50: 1311
    1285,   // 51: 1285
    1260,   // 52: 1260
    1237,   // 53: 1237
    1214,   // 54: 1214
    1192,   // 55: 1192
    1170,   // 56: 1170
    1150,   // 57: 1150
    1130,   // 58: 1130
    1111,   // 59: 1111
    1092,   // 60: 1092
    1074,   // 61: 1074
    1057,   // 62: 1057
    1040,   // 63: 1040
    1024    // 64: 1024
};

// Sum factor reciprocal table (same as INV_TABLE but with specific values needed)
const ap_uint<16> SUM_FACTOR_INV_TABLE[65] = {
    0,      // 0: unused
    65536,  // 1
    32768,  // 2
    21845,  // 3
    16384,  // 4
    13107,  // 5
    10923,  // 6
    9362,   // 7
    8192,   // 8
    7282,   // 9
    6554,   // 10
    5958,   // 11
    5461,   // 12
    5041,   // 13
    4681,   // 14
    4369,   // 15
    4096,   // 16
    3855,   // 17
    3641,   // 18
    3449,   // 19
    3277,   // 20
    3121,   // 21
    2979,   // 22
    2849,   // 23
    2731,   // 24
    2621,   // 25
    2521,   // 26
    2427,   // 27
    2341,   // 28
    2256,   // 29
    2185,   // 30
    2115,   // 31
    2048,   // 32
    1986,   // 33
    1928,   // 34
    1872,   // 35
    1820,   // 36
    1771,   // 37
    1725,   // 38
    1680,   // 39
    1638,   // 40
    1598,   // 41
    1560,   // 42
    1524,   // 43
    1490,   // 44
    1457,   // 45
    1425,   // 46
    1395,   // 47
    1365,   // 48
    1337,   // 49
    1311,   // 50
    1285,   // 51
    1260,   // 52
    1237,   // 53
    1214,   // 54
    1192,   // 55
    1170,   // 56
    1150,   // 57
    1130,   // 58
    1111,   // 59
    1092,   // 60
    1074,   // 61
    1057,   // 62
    1040,   // 63
    1024    // 64
};

// ============================================================
// Division by 5 (Multiply Approximation)
// ============================================================
ap_uint<11> div_by_5(ap_uint<13> grad_abs) {
    #pragma HLS INLINE
    #pragma HLS PIPELINE II=1

    // x / 5 ≈ (x * 205) >> 10
    // Maximum error < 0.1%
    unsigned int product = (unsigned int)grad_abs * 205;
    ap_uint<11> result = product >> 10;

    return result;
}

// ============================================================
// Division by 64 (Right Shift)
// ============================================================
ap_int<11> div_by_64(ap_int<17> numerator) {
    #pragma HLS INLINE
    #pragma HLS PIPELINE II=1

    // x / 64 = x >> 6 (exact division)
    int num_val = (int)numerator;
    ap_int<11> result = num_val >> 6;

    return result;
}

// ============================================================
// Division by Lookup Table
// ============================================================
ap_int<11> div_by_lookup(ap_int<16> numerator, ap_uint<7> denominator) {
    #pragma HLS INLINE
    #pragma HLS PIPELINE II=1

    // Handle division by zero (should not occur in normal operation)
    if (denominator == 0) {
        return 0;
    }

    // Get reciprocal from lookup table
    unsigned int inv = INV_TABLE[(int)denominator];

    // Determine sign
    int num_val = (int)numerator;
    bool is_negative = num_val < 0;
    unsigned int abs_num = is_negative ? (unsigned int)(-num_val) : (unsigned int)num_val;

    // Compute quotient: N * (1/D)
    unsigned int product = abs_num * inv;
    unsigned int abs_result = product >> 16;

    // Apply sign
    ap_int<11> result = is_negative ? -(int)abs_result : (int)abs_result;

    return result;
}

// ============================================================
// Initial Reciprocal Estimate for NR Division
// ============================================================
ap_uint<16> initial_reciprocal(ap_uint<14> denominator) {
    #pragma HLS INLINE
    #pragma HLS PIPELINE II=1

    unsigned int denom = (unsigned int)denominator;

    // For small denominators, use lookup table
    if (denom <= 64) {
        return INV_TABLE[denom];
    }

    // For larger denominators, use shift-based approximation
    // Find the position of the most significant bit
    int msb_pos = 0;
    unsigned int temp = denom;

    // Count leading zeros equivalent - find MSB position
    for (int i = 13; i >= 0; i--) {
        #pragma HLS UNROLL
        if ((temp >> i) & 1) {
            msb_pos = i;
        }
    }

    // Initial estimate: 2^16 / (2^msb_pos) = 2^(16-msb_pos)
    ap_uint<16> estimate = (1u << (16 - msb_pos));

    return estimate;
}

// ============================================================
// Newton-Raphson Division
// ============================================================
ap_int<11> div_by_nr(ap_int<23> numerator, ap_uint<14> denominator) {
    #pragma HLS INLINE
    #pragma HLS PIPELINE II=1

    long long num_val = (long long)numerator;
    unsigned int denom_val = (unsigned int)denominator;

    // Handle division by zero
    if (denom_val == 0) {
        return 0;
    }

    // Handle zero numerator
    if (num_val == 0) {
        return 0;
    }

    // Determine sign
    bool is_negative = num_val < 0;
    unsigned long long abs_num = is_negative ? (unsigned long long)(-num_val) : (unsigned long long)num_val;

    // Step 1: Initial estimate of reciprocal
    unsigned int x0 = initial_reciprocal(denom_val);

    // Step 2: First NR iteration
    // x1 = x0 * (2 - D * x0)
    unsigned long long prod0 = (unsigned long long)denom_val * x0;
    long long two_minus_prod0 = (2LL << 16) - (long long)prod0;
    unsigned long long x1_full = (unsigned long long)x0 * two_minus_prod0;
    unsigned int x1 = x1_full >> 16;

    // Step 3: Second NR iteration (for higher precision)
    // x2 = x1 * (2 - D * x1)
    unsigned long long prod1 = (unsigned long long)denom_val * x1;
    long long two_minus_prod1 = (2LL << 16) - (long long)prod1;
    unsigned long long x2_full = (unsigned long long)x1 * two_minus_prod1;
    unsigned int x2 = x2_full >> 16;

    // Step 4: Compute quotient = N * x2
    unsigned long long quotient_full = abs_num * x2;
    unsigned int abs_result = quotient_full >> 16;

    // Saturate if result is out of range
    if (abs_result > 511) {
        abs_result = 511;
    }

    // Apply sign
    ap_int<11> result = is_negative ? -(int)abs_result : (int)abs_result;

    return result;
}
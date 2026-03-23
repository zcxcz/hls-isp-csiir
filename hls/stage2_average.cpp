// ============================================================
// ISP-CSIIR Stage 2: Multi-scale Directional Average
// ============================================================
// Project: ISP-CSIIR HLS Module
// Version: v1.0
// Date: 2026-03-23
// Description:
//   - Kernel selection based on window size
//   - Weighted average computation
//   - Division using lookup table
// ============================================================

#include "isp_csiir.h"
#include "div_utils.h"

// ============================================================
// Compute Weighted Sum
// ============================================================
static void compute_weighted_sum(
    pixel_s11_t   src_s11_5x5[5][5],
    avg_factor_t  factor[5][5],
    ap_uint<1>    mask[5][5],
    weighted_sum_t &weighted_sum,
    sum_factor_t  &sum_factor
) {
    #pragma HLS INLINE
    #pragma HLS ARRAY_PARTITION variable=src_s11_5x5 complete
    #pragma HLS ARRAY_PARTITION variable=factor complete
    #pragma HLS ARRAY_PARTITION variable=mask complete

    weighted_sum = 0;
    sum_factor = 0;

    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            avg_factor_t masked_factor = factor[i][j] & ((avg_factor_t)mask[i][j]);
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)masked_factor;
            sum_factor += masked_factor;
        }
    }
}

// ============================================================
// Compute Average Value
// ============================================================
static avg_value_t compute_average(
    weighted_sum_t weighted_sum,
    sum_factor_t   sum_factor
) {
    #pragma HLS INLINE

    // Handle edge case where sum_factor is zero
    if (sum_factor == 0) {
        return 0;
    }

    // Use lookup table division
    return div_by_lookup(weighted_sum, sum_factor);
}

// ============================================================
// Select Kernels Based on Window Size
// ============================================================
static void select_kernels(
    win_size_t    win_size,
    ap_uint<8>    win_thresh[4],
    avg_factor_t  (&avg0_factor_c)[5][5],
    avg_factor_t  (&avg1_factor_c)[5][5]
) {
    #pragma HLS INLINE

    // Copy appropriate kernels based on window size thresholds
    if (win_size < win_thresh[0]) {
        // avg0: zeros, avg1: 2x2
        for (int i = 0; i < 5; i++) {
            #pragma HLS UNROLL
            for (int j = 0; j < 5; j++) {
                #pragma HLS UNROLL
                avg0_factor_c[i][j] = 0;
                avg1_factor_c[i][j] = AVG_FACTOR_2x2[i][j];
            }
        }
    } else if (win_size < win_thresh[1]) {
        // avg0: 2x2, avg1: 3x3
        for (int i = 0; i < 5; i++) {
            #pragma HLS UNROLL
            for (int j = 0; j < 5; j++) {
                #pragma HLS UNROLL
                avg0_factor_c[i][j] = AVG_FACTOR_2x2[i][j];
                avg1_factor_c[i][j] = AVG_FACTOR_3x3[i][j];
            }
        }
    } else if (win_size < win_thresh[2]) {
        // avg0: 3x3, avg1: 4x4
        for (int i = 0; i < 5; i++) {
            #pragma HLS UNROLL
            for (int j = 0; j < 5; j++) {
                #pragma HLS UNROLL
                avg0_factor_c[i][j] = AVG_FACTOR_3x3[i][j];
                avg1_factor_c[i][j] = AVG_FACTOR_4x4[i][j];
            }
        }
    } else if (win_size < win_thresh[3]) {
        // avg0: 4x4, avg1: 5x5
        for (int i = 0; i < 5; i++) {
            #pragma HLS UNROLL
            for (int j = 0; j < 5; j++) {
                #pragma HLS UNROLL
                avg0_factor_c[i][j] = AVG_FACTOR_4x4[i][j];
                avg1_factor_c[i][j] = AVG_FACTOR_5x5[i][j];
            }
        }
    } else {
        // avg0: 5x5, avg1: zeros
        for (int i = 0; i < 5; i++) {
            #pragma HLS UNROLL
            for (int j = 0; j < 5; j++) {
                #pragma HLS UNROLL
                avg0_factor_c[i][j] = AVG_FACTOR_5x5[i][j];
                avg1_factor_c[i][j] = 0;
            }
        }
    }
}

// ============================================================
// Stage 2 Main Function
// ============================================================
void stage2_average(
    pixel_s11_t   src_s11_5x5[5][5],
    win_size_t    win_size,
    ap_uint<8>    win_thresh[4],
    avg_value_t   &avg0_c, avg_value_t &avg0_u, avg_value_t &avg0_d,
    avg_value_t   &avg0_l, avg_value_t &avg0_r,
    avg_value_t   &avg1_c, avg_value_t &avg1_u, avg_value_t &avg1_d,
    avg_value_t   &avg1_l, avg_value_t &avg1_r
) {
    #pragma HLS INLINE
    #pragma HLS ARRAY_PARTITION variable=src_s11_5x5 complete

    // --------------------------------------------------------
    // Step 1: Select kernels based on window size
    // --------------------------------------------------------
    avg_factor_t avg0_factor_c[5][5];
    avg_factor_t avg1_factor_c[5][5];
    #pragma HLS ARRAY_PARTITION variable=avg0_factor_c complete
    #pragma HLS ARRAY_PARTITION variable=avg1_factor_c complete

    select_kernels(win_size, win_thresh, avg0_factor_c, avg1_factor_c);

    // --------------------------------------------------------
    // Step 2: Compute avg0 values (smaller kernel)
    // --------------------------------------------------------
    weighted_sum_t weighted_sum;
    sum_factor_t sum_factor;

    // avg0_c: Center average (no mask - uses full kernel)
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)avg0_factor_c[i][j];
            sum_factor += avg0_factor_c[i][j];
        }
    }
    avg0_c = compute_average(weighted_sum, sum_factor);

    // avg0_u: Up average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            avg_factor_t masked_factor = avg0_factor_c[i][j] & (avg_factor_t)MASK_U[i][j];
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)masked_factor;
            sum_factor += masked_factor;
        }
    }
    avg0_u = compute_average(weighted_sum, sum_factor);

    // avg0_d: Down average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            avg_factor_t masked_factor = avg0_factor_c[i][j] & (avg_factor_t)MASK_D[i][j];
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)masked_factor;
            sum_factor += masked_factor;
        }
    }
    avg0_d = compute_average(weighted_sum, sum_factor);

    // avg0_l: Left average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            avg_factor_t masked_factor = avg0_factor_c[i][j] & (avg_factor_t)MASK_L[i][j];
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)masked_factor;
            sum_factor += masked_factor;
        }
    }
    avg0_l = compute_average(weighted_sum, sum_factor);

    // avg0_r: Right average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            avg_factor_t masked_factor = avg0_factor_c[i][j] & (avg_factor_t)MASK_R[i][j];
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)masked_factor;
            sum_factor += masked_factor;
        }
    }
    avg0_r = compute_average(weighted_sum, sum_factor);

    // --------------------------------------------------------
    // Step 3: Compute avg1 values (larger kernel)
    // --------------------------------------------------------
    // avg1_c: Center average (no mask)
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)avg1_factor_c[i][j];
            sum_factor += avg1_factor_c[i][j];
        }
    }
    avg1_c = compute_average(weighted_sum, sum_factor);

    // avg1_u: Up average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            avg_factor_t masked_factor = avg1_factor_c[i][j] & (avg_factor_t)MASK_U[i][j];
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)masked_factor;
            sum_factor += masked_factor;
        }
    }
    avg1_u = compute_average(weighted_sum, sum_factor);

    // avg1_d: Down average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            avg_factor_t masked_factor = avg1_factor_c[i][j] & (avg_factor_t)MASK_D[i][j];
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)masked_factor;
            sum_factor += masked_factor;
        }
    }
    avg1_d = compute_average(weighted_sum, sum_factor);

    // avg1_l: Left average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            avg_factor_t masked_factor = avg1_factor_c[i][j] & (avg_factor_t)MASK_L[i][j];
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)masked_factor;
            sum_factor += masked_factor;
        }
    }
    avg1_l = compute_average(weighted_sum, sum_factor);

    // avg1_r: Right average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            avg_factor_t masked_factor = avg1_factor_c[i][j] & (avg_factor_t)MASK_R[i][j];
            weighted_sum += (weighted_sum_t)src_s11_5x5[i][j] * (weighted_sum_t)masked_factor;
            sum_factor += masked_factor;
        }
    }
    avg1_r = compute_average(weighted_sum, sum_factor);
}
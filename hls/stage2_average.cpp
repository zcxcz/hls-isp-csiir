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
// Compute Average Value
// ============================================================
static avg_value_t compute_average(
    int weighted_sum,
    int sum_factor
) {
    #pragma HLS INLINE

    if (sum_factor == 0) {
        return 0;
    }

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

    int ws = (int)win_size;
    int t0 = (int)win_thresh[0];
    int t1 = (int)win_thresh[1];
    int t2 = (int)win_thresh[2];
    int t3 = (int)win_thresh[3];

    if (ws < t0) {
        for (int i = 0; i < 5; i++) {
            #pragma HLS UNROLL
            for (int j = 0; j < 5; j++) {
                #pragma HLS UNROLL
                avg0_factor_c[i][j] = 0;
                avg1_factor_c[i][j] = AVG_FACTOR_2x2[i][j];
            }
        }
    } else if (ws < t1) {
        for (int i = 0; i < 5; i++) {
            #pragma HLS UNROLL
            for (int j = 0; j < 5; j++) {
                #pragma HLS UNROLL
                avg0_factor_c[i][j] = AVG_FACTOR_2x2[i][j];
                avg1_factor_c[i][j] = AVG_FACTOR_3x3[i][j];
            }
        }
    } else if (ws < t2) {
        for (int i = 0; i < 5; i++) {
            #pragma HLS UNROLL
            for (int j = 0; j < 5; j++) {
                #pragma HLS UNROLL
                avg0_factor_c[i][j] = AVG_FACTOR_3x3[i][j];
                avg1_factor_c[i][j] = AVG_FACTOR_4x4[i][j];
            }
        }
    } else if (ws < t3) {
        for (int i = 0; i < 5; i++) {
            #pragma HLS UNROLL
            for (int j = 0; j < 5; j++) {
                #pragma HLS UNROLL
                avg0_factor_c[i][j] = AVG_FACTOR_4x4[i][j];
                avg1_factor_c[i][j] = AVG_FACTOR_5x5[i][j];
            }
        }
    } else {
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

// Helper function to get masked factor
static int get_masked_factor(avg_factor_t factor, int mask_val) {
    return (int)factor & mask_val;
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

    // Select kernels
    avg_factor_t avg0_factor_c[5][5];
    avg_factor_t avg1_factor_c[5][5];
    #pragma HLS ARRAY_PARTITION variable=avg0_factor_c complete
    #pragma HLS ARRAY_PARTITION variable=avg1_factor_c complete

    select_kernels(win_size, win_thresh, avg0_factor_c, avg1_factor_c);

    int weighted_sum;
    int sum_factor;

    // avg0_c: Center average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            int factor = (int)avg0_factor_c[i][j];
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
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
            int factor = ((int)avg0_factor_c[i][j]) & ((int)MASK_U[i][j]);
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
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
            int factor = ((int)avg0_factor_c[i][j]) & ((int)MASK_D[i][j]);
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
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
            int factor = ((int)avg0_factor_c[i][j]) & ((int)MASK_L[i][j]);
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
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
            int factor = ((int)avg0_factor_c[i][j]) & ((int)MASK_R[i][j]);
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
        }
    }
    avg0_r = compute_average(weighted_sum, sum_factor);

    // avg1_c: Center average
    weighted_sum = 0;
    sum_factor = 0;
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            int factor = (int)avg1_factor_c[i][j];
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
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
            int factor = ((int)avg1_factor_c[i][j]) & ((int)MASK_U[i][j]);
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
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
            int factor = ((int)avg1_factor_c[i][j]) & ((int)MASK_D[i][j]);
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
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
            int factor = ((int)avg1_factor_c[i][j]) & ((int)MASK_L[i][j]);
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
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
            int factor = ((int)avg1_factor_c[i][j]) & ((int)MASK_R[i][j]);
            int pixel = (int)src_s11_5x5[i][j];
            weighted_sum = weighted_sum + pixel * factor;
            sum_factor = sum_factor + factor;
        }
    }
    avg1_r = compute_average(weighted_sum, sum_factor);
}
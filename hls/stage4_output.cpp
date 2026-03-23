// ============================================================
// ISP-CSIIR Stage 4: IIR Filtering and Blend Output
// ============================================================
// Project: ISP-CSIIR HLS Module
// Version: v1.0
// Date: 2026-03-23
// Description:
//   - Horizontal blending
//   - Window blending
//   - Final output
// ============================================================

#include "isp_csiir.h"
#include "div_utils.h"

// ============================================================
// Compute Horizontal Blend
// ============================================================
static void compute_horizontal_blend(
    blend_grad_t blend_grad,
    avg_value_t  avg_u,
    ap_uint<8>   ratio,
    blend_grad_t &blend_hor
) {
    #pragma HLS INLINE

    // blend_hor = (ratio * blend_grad + (64 - ratio) * avg_u) / 64
    ap_int<17> numerator = (ap_int<17>)ratio * (ap_int<17>)blend_grad +
                           (ap_int<17>)(RATIO_SCALE - ratio) * (ap_int<17>)avg_u;

    // Divide by 64 (exact right shift)
    blend_hor = numerator >> 6;
}

// ============================================================
// Compute Window Blend with Inline Factor Access
// ============================================================
static void compute_window_blend_inline(
    blend_grad_t blend_hor,
    pixel_s11_t  src_s11_5x5[5][5],
    const avg_factor_t blend_factor[5][5],
    ap_int<20>   &blend_win_sum
) {
    #pragma HLS INLINE
    #pragma HLS ARRAY_PARTITION variable=src_s11_5x5 complete

    blend_win_sum = 0;

    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            // blend_win_pixel = blend_value * blend_factor + src_value * (4 - blend_factor)
            ap_int<17> pixel_blend = (ap_int<17>)blend_hor * (ap_int<17>)blend_factor[i][j] +
                                     (ap_int<17>)src_s11_5x5[i][j] * (ap_int<17>)(4 - blend_factor[i][j]);
            blend_win_sum += pixel_blend;
        }
    }
}

// ============================================================
// Copy Blend Factor Array
// ============================================================
static void copy_blend_factor(
    const avg_factor_t src[5][5],
    avg_factor_t dst[5][5]
) {
    #pragma HLS INLINE
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            dst[i][j] = src[i][j];
        }
    }
}

// ============================================================
// Stage 4 Main Function
// ============================================================
void stage4_output(
    blend_grad_t  blend0_grad,
    blend_grad_t  blend1_grad,
    avg_value_t   avg0_u,
    avg_value_t   avg1_u,
    win_size_t    win_size,
    ap_uint<8>    win_thresh[4],
    ap_uint<8>    blend_ratio[4],
    ap_uint<8>    edge_protect,
    pixel_s11_t   src_s11_5x5[5][5],
    pixel_u10_t   &dout
) {
    #pragma HLS INLINE
    #pragma HLS ARRAY_PARTITION variable=src_s11_5x5 complete

    // --------------------------------------------------------
    // Step 1: Determine blend ratio index
    // blend_ratio_idx = win_size / 8 - 2
    // Range: [0, 3] for win_size in [16, 40]
    // --------------------------------------------------------
    ap_uint<3> blend_ratio_idx = (win_size >> 3) - 2;
    if (blend_ratio_idx > 3) blend_ratio_idx = 3;

    ap_uint<8> ratio;
    switch (blend_ratio_idx) {
        case 0:  ratio = blend_ratio[0]; break;
        case 1:  ratio = blend_ratio[1]; break;
        case 2:  ratio = blend_ratio[2]; break;
        default: ratio = blend_ratio[3]; break;
    }

    // --------------------------------------------------------
    // Step 2: Horizontal blending
    // --------------------------------------------------------
    blend_grad_t blend0_hor, blend1_hor;
    compute_horizontal_blend(blend0_grad, avg0_u, ratio, blend0_hor);
    compute_horizontal_blend(blend1_grad, avg1_u, ratio, blend1_hor);

    // --------------------------------------------------------
    // Step 3: Prepare blend factor arrays
    // Using horizontal direction by default
    // --------------------------------------------------------
    avg_factor_t blend_factor_hv[5][5];
    avg_factor_t blend_factor_2x2[5][5];
    avg_factor_t blend_factor_3x3[5][5];
    avg_factor_t blend_factor_4x4[5][5];
    avg_factor_t blend_factor_5x5[5][5];
    #pragma HLS ARRAY_PARTITION variable=blend_factor_hv complete
    #pragma HLS ARRAY_PARTITION variable=blend_factor_2x2 complete
    #pragma HLS ARRAY_PARTITION variable=blend_factor_3x3 complete
    #pragma HLS ARRAY_PARTITION variable=blend_factor_4x4 complete
    #pragma HLS ARRAY_PARTITION variable=blend_factor_5x5 complete

    // Copy from constants
    copy_blend_factor(BLEND_FACTOR_2x2_H, blend_factor_hv);
    copy_blend_factor(BLEND_FACTOR_2x2, blend_factor_2x2);
    copy_blend_factor(BLEND_FACTOR_3x3, blend_factor_3x3);
    copy_blend_factor(BLEND_FACTOR_4x4, blend_factor_4x4);
    copy_blend_factor(BLEND_FACTOR_5x5, blend_factor_5x5);

    // --------------------------------------------------------
    // Step 4: Window blending based on window size
    // --------------------------------------------------------
    ap_int<20> blend0_win_sum = 0;
    ap_int<20> blend1_win_sum = 0;
    ap_int<20> blend0_win_sum_alt = 0;  // For edge protection

    if (win_size < win_thresh[0]) {
        // blend0: using hv factor + edge protection
        compute_window_blend_inline(blend0_hor, src_s11_5x5, blend_factor_hv, blend0_win_sum);
        compute_window_blend_inline(blend0_hor, src_s11_5x5, blend_factor_2x2, blend0_win_sum_alt);

        // Apply edge protection blend
        blend0_win_sum = (blend0_win_sum * edge_protect + blend0_win_sum_alt * (RATIO_SCALE - edge_protect)) >> 6;

    } else if (win_size < win_thresh[1]) {
        compute_window_blend_inline(blend0_hor, src_s11_5x5, blend_factor_hv, blend0_win_sum);
        compute_window_blend_inline(blend0_hor, src_s11_5x5, blend_factor_2x2, blend0_win_sum_alt);
        blend0_win_sum = (blend0_win_sum * edge_protect + blend0_win_sum_alt * (RATIO_SCALE - edge_protect)) >> 6;

        compute_window_blend_inline(blend1_hor, src_s11_5x5, blend_factor_3x3, blend1_win_sum);

    } else if (win_size < win_thresh[2]) {
        compute_window_blend_inline(blend0_hor, src_s11_5x5, blend_factor_3x3, blend0_win_sum);
        compute_window_blend_inline(blend1_hor, src_s11_5x5, blend_factor_4x4, blend1_win_sum);

    } else if (win_size < win_thresh[3]) {
        compute_window_blend_inline(blend0_hor, src_s11_5x5, blend_factor_4x4, blend0_win_sum);
        compute_window_blend_inline(blend1_hor, src_s11_5x5, blend_factor_5x5, blend1_win_sum);

    } else {
        compute_window_blend_inline(blend1_hor, src_s11_5x5, blend_factor_5x5, blend1_win_sum);
    }

    // --------------------------------------------------------
    // Step 5: Final blend
    // win_size_remain_8 = win_size % 8
    // blend_uv = blend0_win * remainder + blend1_win * (8 - remainder)
    // --------------------------------------------------------
    win_remain_t win_remain = win_size & 0x7;  // win_size % 8

    ap_int<23> blend_uv_sum;

    if (win_size < win_thresh[0]) {
        // Use blend0_win only
        blend_uv_sum = blend0_win_sum;
    } else if (win_size >= win_thresh[3]) {
        // Use blend1_win only
        blend_uv_sum = blend1_win_sum;
    } else {
        // Interpolate between blend0_win and blend1_win
        blend_uv_sum = (blend0_win_sum * win_remain + blend1_win_sum * (8 - win_remain)) >> 3;
    }

    // Normalize by dividing by the sum of blend factors
    // The total blend factor sum is 4 (center weight)
    blend_grad_t blend_uv = blend_uv_sum >> 2;  // Divide by 4

    // --------------------------------------------------------
    // Step 6: Convert to unsigned and clip
    // blend_uv is in range [-512, 511]
    // Output: clip(blend_uv + 512, 0, 1023)
    // --------------------------------------------------------
    ap_int<12> output_signed = (ap_int<12>)blend_uv + (ap_int<12>)512;

    // Clip to [0, 1023]
    if (output_signed < 0) {
        dout = 0;
    } else if (output_signed > 1023) {
        dout = 1023;
    } else {
        dout = (pixel_u10_t)output_signed;
    }
}
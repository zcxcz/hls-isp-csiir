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
static int compute_horizontal_blend(
    int blend_grad,
    int avg_u,
    int ratio
) {
    #pragma HLS INLINE
    int numerator = ratio * blend_grad + (64 - ratio) * avg_u;
    return numerator >> 6;
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

    // Step 1: Determine blend ratio index
    int ws = (int)win_size;
    int blend_ratio_idx = (ws >> 3) - 2;
    if (blend_ratio_idx < 0) blend_ratio_idx = 0;
    if (blend_ratio_idx > 3) blend_ratio_idx = 3;

    int ratio;
    switch (blend_ratio_idx) {
        case 0:  ratio = (int)blend_ratio[0]; break;
        case 1:  ratio = (int)blend_ratio[1]; break;
        case 2:  ratio = (int)blend_ratio[2]; break;
        default: ratio = (int)blend_ratio[3]; break;
    }

    // Step 2: Horizontal blending
    int b0g = (int)blend0_grad;
    int b1g = (int)blend1_grad;
    int a0u = (int)avg0_u;
    int a1u = (int)avg1_u;

    int blend0_hor = compute_horizontal_blend(b0g, a0u, ratio);
    int blend1_hor = compute_horizontal_blend(b1g, a1u, ratio);

    // Step 3: Prepare blend factor arrays
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

    copy_blend_factor(BLEND_FACTOR_2x2_H, blend_factor_hv);
    copy_blend_factor(BLEND_FACTOR_2x2, blend_factor_2x2);
    copy_blend_factor(BLEND_FACTOR_3x3, blend_factor_3x3);
    copy_blend_factor(BLEND_FACTOR_4x4, blend_factor_4x4);
    copy_blend_factor(BLEND_FACTOR_5x5, blend_factor_5x5);

    // Step 4: Window blending
    int t0 = (int)win_thresh[0];
    int t1 = (int)win_thresh[1];
    int t2 = (int)win_thresh[2];
    int t3 = (int)win_thresh[3];

    int blend_uv;

    if (ws < t0) {
        blend_uv = blend0_hor;
    } else if (ws >= t3) {
        blend_uv = blend1_hor;
    } else {
        int win_remain = ws & 0x7;
        blend_uv = (blend0_hor * win_remain + blend1_hor * (8 - win_remain)) >> 3;
    }

    // Step 5: Convert to unsigned and clip
    int output_signed = blend_uv + 512;

    if (output_signed < 0) {
        dout = 0;
    } else if (output_signed > 1023) {
        dout = 1023;
    } else {
        dout = output_signed;
    }
}
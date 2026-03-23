// ============================================================
// ISP-CSIIR HLS Main Function Header
// ============================================================
// Project: ISP-CSIIR HLS Module
// Version: v1.0
// Date: 2026-03-23
// Description: Main function declarations for ISP-CSIIR module
// ============================================================

#ifndef ISP_CSIIR_H
#define ISP_CSIIR_H

#include "isp_csiir_types.h"

// ============================================================
// Main Processing Function
// ============================================================
void isp_csiir_top(
    // AXI-Stream Input
    hls::stream<axis_pixel_t> &din_stream,

    // AXI-Stream Output
    hls::stream<axis_pixel_t> &dout_stream,

    // Configuration Parameters (AXI-Lite)
    ap_uint<16> img_width,
    ap_uint<16> img_height,
    ap_uint<8>  win_thresh0,
    ap_uint<8>  win_thresh1,
    ap_uint<8>  win_thresh2,
    ap_uint<8>  win_thresh3,
    ap_uint<8>  grad_clip0,
    ap_uint<8>  grad_clip1,
    ap_uint<8>  grad_clip2,
    ap_uint<8>  grad_clip3,
    ap_uint<8>  blend_ratio0,
    ap_uint<8>  blend_ratio1,
    ap_uint<8>  blend_ratio2,
    ap_uint<8>  blend_ratio3,
    ap_uint<8>  edge_protect
);

// ============================================================
// Line Buffer and Window Function
// ============================================================
void line_buffer_window(
    hls::stream<axis_pixel_t> &din_stream,
    pixel_u10_t window[5][5],
    pixel_s11_t window_s11[5][5],
    ap_uint<16> col_count,
    ap_uint<16> row_count,
    ap_uint<16> img_width,
    ap_uint<16> img_height,
    ap_uint<1> &window_valid
);

// ============================================================
// Stage 1: Gradient Computation
// ============================================================
void stage1_gradient(
    pixel_u10_t  src_5x5[5][5],
    pixel_s11_t  src_s11_5x5[5][5],
    grad_t       &grad,
    win_size_t   &win_size,
    ap_uint<8>   grad_clip[4]
);

// ============================================================
// Stage 2: Multi-scale Directional Average
// ============================================================
void stage2_average(
    pixel_s11_t   src_s11_5x5[5][5],
    win_size_t    win_size,
    ap_uint<8>    win_thresh[4],
    avg_value_t   &avg0_c, avg_value_t &avg0_u, avg_value_t &avg0_d,
    avg_value_t   &avg0_l, avg_value_t &avg0_r,
    avg_value_t   &avg1_c, avg_value_t &avg1_u, avg_value_t &avg1_d,
    avg_value_t   &avg1_l, avg_value_t &avg1_r
);

// ============================================================
// Stage 3: Gradient-weighted Directional Fusion
// ============================================================
void stage3_blend(
    grad_t        grad_5x5[5][5],
    avg_value_t   avg0_c, avg_value_t avg0_u, avg_value_t avg0_d,
    avg_value_t   avg0_l, avg_value_t avg0_r,
    avg_value_t   avg1_c, avg_value_t avg1_u, avg_value_t avg1_d,
    avg_value_t   avg1_l, avg_value_t avg1_r,
    blend_grad_t  &blend0_grad,
    blend_grad_t  &blend1_grad
);

// ============================================================
// Stage 4: IIR Filtering and Blend Output
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
);

// ============================================================
// Gradient Window Function (for Stage 3)
// ============================================================
void get_gradient_window(
    grad_t grad_center[5][5],
    ap_uint<16> col, ap_uint<16> row,
    ap_uint<16> img_width, ap_uint<16> img_height,
    grad_t grad_u, grad_t grad_d, grad_t grad_l, grad_t grad_r, grad_t grad_c
);

// ============================================================
// 5-Element Sorting Network (Inverse Sort)
// ============================================================
void sort5_inverse(
    grad_t in0, grad_t in1, grad_t in2, grad_t in3, grad_t in4,
    grad_t &out0, grad_t &out1, grad_t &out2, grad_t &out3, grad_t &out4
);

// ============================================================
// Clip Function
// ============================================================
template<typename T>
T clip(T value, T min_val, T max_val) {
    #pragma HLS INLINE
    if (value < min_val) return min_val;
    if (value > max_val) return max_val;
    return value;
}

#endif // ISP_CSIIR_H
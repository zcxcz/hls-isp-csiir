// ============================================================
// ISP-CSIIR Stage 1: Gradient Computation
// ============================================================
// Project: ISP-CSIIR HLS Module
// Version: v1.0
// Date: 2026-03-23
// Description:
//   - 5x5 Sobel convolution
//   - grad/5 multiply approximation
//   - Window size LUT
// ============================================================

#include "isp_csiir.h"
#include "div_utils.h"

// ============================================================
// Compute Sobel Gradients
// ============================================================
static void compute_sobel_gradients(
    pixel_u10_t src_5x5[5][5],
    grad_hv_t   &grad_h,
    grad_hv_t   &grad_v
) {
    #pragma HLS INLINE

    // Sobel X: sum(row0) - sum(row4)
    row_sum_t row0_sum = 0;
    row_sum_t row4_sum = 0;

    // Sobel Y: sum(col0) - sum(col4)
    row_sum_t col0_sum = 0;
    row_sum_t col4_sum = 0;

    // Compute row and column sums
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        row0_sum += src_5x5[0][i];
        row4_sum += src_5x5[4][i];
        col0_sum += src_5x5[i][0];
        col4_sum += src_5x5[i][4];
    }

    // Compute gradients
    grad_h = (grad_hv_t)row0_sum - (grad_hv_t)row4_sum;
    grad_v = (grad_hv_t)col0_sum - (grad_hv_t)col4_sum;
}

// ============================================================
// Compute Combined Gradient
// ============================================================
static grad_t compute_combined_gradient(
    grad_hv_t grad_h,
    grad_hv_t grad_v
) {
    #pragma HLS INLINE

    // Compute absolute values
    grad_abs_t grad_h_abs = (grad_h < 0) ? (grad_abs_t)(-grad_h) : (grad_abs_t)grad_h;
    grad_abs_t grad_v_abs = (grad_v < 0) ? (grad_abs_t)(-grad_v) : (grad_abs_t)grad_v;

    // Divide by 5 using multiply approximation
    ap_uint<11> grad_h_div5 = div_by_5(grad_h_abs);
    ap_uint<11> grad_v_div5 = div_by_5(grad_v_abs);

    // Combined gradient
    grad_t grad = grad_h_div5 + grad_v_div5;

    return grad;
}

// ============================================================
// Window Size LUT
// ============================================================
static win_size_t compute_window_size(
    grad_t grad_max,
    ap_uint<8> grad_clip[4]
) {
    #pragma HLS INLINE

    win_size_t win_size;

    // LUT-based window size determination
    // grad_max = max(grad(i-1,j), grad(i,j), grad(i+1,j))
    if (grad_max <= grad_clip[0]) {
        win_size = 16;  // Minimum window size
    } else if (grad_max <= grad_clip[1]) {
        win_size = 23;
    } else if (grad_max <= grad_clip[2]) {
        win_size = 31;
    } else if (grad_max <= grad_clip[3]) {
        win_size = 39;
    } else {
        win_size = 40;  // Maximum window size
    }

    return win_size;
}

// ============================================================
// Stage 1 Main Function
// ============================================================
void stage1_gradient(
    pixel_u10_t  src_5x5[5][5],
    pixel_s11_t  src_s11_5x5[5][5],
    grad_t       &grad,
    win_size_t   &win_size,
    ap_uint<8>   grad_clip[4]
) {
    #pragma HLS INLINE
    #pragma HLS ARRAY_PARTITION variable=src_5x5 complete
    #pragma HLS ARRAY_PARTITION variable=src_s11_5x5 complete

    // --------------------------------------------------------
    // Step 1: Convert to signed representation
    // --------------------------------------------------------
    for (int i = 0; i < 5; i++) {
        #pragma HLS UNROLL
        for (int j = 0; j < 5; j++) {
            #pragma HLS UNROLL
            src_s11_5x5[i][j] = (pixel_s11_t)src_5x5[i][j] - (pixel_s11_t)512;
        }
    }

    // --------------------------------------------------------
    // Step 2: Compute Sobel gradients
    // --------------------------------------------------------
    grad_hv_t grad_h, grad_v;
    compute_sobel_gradients(src_5x5, grad_h, grad_v);

    // --------------------------------------------------------
    // Step 3: Compute combined gradient
    // --------------------------------------------------------
    grad = compute_combined_gradient(grad_h, grad_v);

    // --------------------------------------------------------
    // Step 4: Compute window size (using center pixel gradient)
    // For now, use the current gradient directly
    // In full implementation, this should use max of 3 gradients
    // --------------------------------------------------------
    win_size = compute_window_size(grad, grad_clip);
}
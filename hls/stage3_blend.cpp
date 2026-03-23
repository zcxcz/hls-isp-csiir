// ============================================================
// ISP-CSIIR Stage 3: Gradient-weighted Directional Fusion
// ============================================================
// Project: ISP-CSIIR HLS Module
// Version: v1.0
// Date: 2026-03-23
// Description:
//   - 5-element sorting network
//   - Weighted fusion
//   - NR iteration division
// ============================================================

#include "isp_csiir.h"
#include "div_utils.h"

// ============================================================
// Swap Function for Sorting
// ============================================================
static void swap_grad(grad_t &a, grad_t &b) {
    #pragma HLS INLINE
    grad_t temp = a;
    a = b;
    b = temp;
}

// ============================================================
// 5-Element Sorting Network (Inverse Sort - Largest First)
// ============================================================
// Uses a sorting network with 9 comparisons
// Output: out0 >= out1 >= out2 >= out3 >= out4
// ============================================================
void sort5_inverse(
    grad_t in0, grad_t in1, grad_t in2, grad_t in3, grad_t in4,
    grad_t &out0, grad_t &out1, grad_t &out2, grad_t &out3, grad_t &out4
) {
    #pragma HLS INLINE
    #pragma HLS PIPELINE II=1

    // Copy inputs
    grad_t a = in0, b = in1, c = in2, d = in3, e = in4;

    // Sorting network (bitonic sort based)
    // Phase 1
    if (a < b) swap_grad(a, b);
    if (c < d) swap_grad(c, d);

    // Phase 2
    if (a < c) swap_grad(a, c);
    if (b < d) swap_grad(b, d);

    // Phase 3
    if (b < c) swap_grad(b, c);
    if (a < e) swap_grad(a, e);

    // Phase 4
    if (c < e) swap_grad(c, e);
    if (b < e) swap_grad(b, e);
    if (d < e) swap_grad(d, e);

    // Phase 5
    if (c < d) swap_grad(c, d);

    // Output in descending order
    out0 = a; out1 = b; out2 = c; out3 = d; out4 = e;
}

// ============================================================
// Compute Gradient Sum and Weighted Average
// ============================================================
static void compute_blend_gradient(
    avg_value_t avg_c, avg_value_t avg_u, avg_value_t avg_d,
    avg_value_t avg_l, avg_value_t avg_r,
    grad_t grad_c, grad_t grad_u, grad_t grad_d,
    grad_t grad_l, grad_t grad_r,
    blend_grad_t &blend_grad
) {
    #pragma HLS INLINE

    // Compute gradient sum
    grad_sum_t grad_sum = (grad_sum_t)grad_c + (grad_sum_t)grad_u +
                          (grad_sum_t)grad_d + (grad_sum_t)grad_l +
                          (grad_sum_t)grad_r;

    if (grad_sum == 0) {
        // Equal weight average
        avg_weighted_t sum_avg = (avg_weighted_t)avg_c + (avg_weighted_t)avg_u +
                                 (avg_weighted_t)avg_d + (avg_weighted_t)avg_l +
                                 (avg_weighted_t)avg_r;
        blend_grad = (blend_grad_t)(sum_avg / 5);
    } else {
        // Gradient-weighted average
        avg_weighted_t weighted_sum = (avg_weighted_t)avg_c * (avg_weighted_t)grad_c +
                                      (avg_weighted_t)avg_u * (avg_weighted_t)grad_u +
                                      (avg_weighted_t)avg_d * (avg_weighted_t)grad_d +
                                      (avg_weighted_t)avg_l * (avg_weighted_t)grad_l +
                                      (avg_weighted_t)avg_r * (avg_weighted_t)grad_r;

        // Use Newton-Raphson division for larger denominator
        blend_grad = div_by_nr(weighted_sum, grad_sum);
    }
}

// ============================================================
// Stage 3 Main Function
// ============================================================
void stage3_blend(
    grad_t        grad_5x5[5][5],
    avg_value_t   avg0_c, avg_value_t avg0_u, avg_value_t avg0_d,
    avg_value_t   avg0_l, avg_value_t avg0_r,
    avg_value_t   avg1_c, avg_value_t avg1_u, avg_value_t avg1_d,
    avg_value_t   avg1_l, avg_value_t avg1_r,
    blend_grad_t  &blend0_grad,
    blend_grad_t  &blend1_grad
) {
    #pragma HLS INLINE
    #pragma HLS ARRAY_PARTITION variable=grad_5x5 complete

    // --------------------------------------------------------
    // Step 1: Extract gradients from window
    // grad_5x5[2][2] = center
    // grad_5x5[0][2] = up (two rows above, use neighbor)
    // grad_5x5[4][2] = down (two rows below, use neighbor)
    // grad_5x5[2][0] = left (two columns left, use neighbor)
    // grad_5x5[2][4] = right (two columns right, use neighbor)
    //
    // Actually, for gradient we need immediate neighbors:
    // grad_u = grad(i, j-1), grad_d = grad(i, j+1)
    // grad_l = grad(i-1, j), grad_r = grad(i+1, j)
    // grad_c = grad(i, j)
    // --------------------------------------------------------
    grad_t grad_c = grad_5x5[2][2];  // Center
    grad_t grad_u = grad_5x5[1][2];  // Up (one row above)
    grad_t grad_d = grad_5x5[3][2];  // Down (one row below)
    grad_t grad_l = grad_5x5[2][1];  // Left (one column left)
    grad_t grad_r = grad_5x5[2][3];  // Right (one column right)

    // --------------------------------------------------------
    // Step 2: Sort gradients (inverse order - largest first)
    // Note: The algorithm uses inverse sorting, but we need to
    // maintain the mapping between gradients and their directions
    // for the weighted fusion.
    // --------------------------------------------------------
    grad_t sorted_g0, sorted_g1, sorted_g2, sorted_g3, sorted_g4;
    sort5_inverse(grad_u, grad_d, grad_l, grad_r, grad_c,
                  sorted_g0, sorted_g1, sorted_g2, sorted_g3, sorted_g4);

    // --------------------------------------------------------
    // Step 3: Compute gradient sum
    // --------------------------------------------------------
    grad_sum_t grad_sum = (grad_sum_t)grad_c + (grad_sum_t)grad_u +
                          (grad_sum_t)grad_d + (grad_sum_t)grad_l +
                          (grad_sum_t)grad_r;

    // --------------------------------------------------------
    // Step 4: Compute blend0_grad (smaller kernel average)
    // --------------------------------------------------------
    compute_blend_gradient(
        avg0_c, avg0_u, avg0_d, avg0_l, avg0_r,
        grad_c, grad_u, grad_d, grad_l, grad_r,
        blend0_grad
    );

    // --------------------------------------------------------
    // Step 5: Compute blend1_grad (larger kernel average)
    // --------------------------------------------------------
    compute_blend_gradient(
        avg1_c, avg1_u, avg1_d, avg1_l, avg1_r,
        grad_c, grad_u, grad_d, grad_l, grad_r,
        blend1_grad
    );
}
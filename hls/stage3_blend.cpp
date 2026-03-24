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
void sort5_inverse(
    grad_t in0, grad_t in1, grad_t in2, grad_t in3, grad_t in4,
    grad_t &out0, grad_t &out1, grad_t &out2, grad_t &out3, grad_t &out4
) {
    #pragma HLS INLINE
    #pragma HLS PIPELINE II=1

    grad_t a = in0, b = in1, c = in2, d = in3, e = in4;

    if (a < b) swap_grad(a, b);
    if (c < d) swap_grad(c, d);

    if (a < c) swap_grad(a, c);
    if (b < d) swap_grad(b, d);

    if (b < c) swap_grad(b, c);
    if (a < e) swap_grad(a, e);

    if (c < e) swap_grad(c, e);
    if (b < e) swap_grad(b, e);
    if (d < e) swap_grad(d, e);

    if (c < d) swap_grad(c, d);

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

    int gc = (int)grad_c;
    int gu = (int)grad_u;
    int gd = (int)grad_d;
    int gl = (int)grad_l;
    int gr = (int)grad_r;

    int ac = (int)avg_c;
    int au = (int)avg_u;
    int ad = (int)avg_d;
    int al = (int)avg_l;
    int ar = (int)avg_r;

    int grad_sum = gc + gu + gd + gl + gr;

    if (grad_sum == 0) {
        int sum_avg = ac + au + ad + al + ar;
        blend_grad = sum_avg / 5;
    } else {
        long long weighted_sum = (long long)ac * gc + (long long)au * gu +
                                  (long long)ad * gd + (long long)al * gl +
                                  (long long)ar * gr;
        blend_grad = div_by_nr(weighted_sum, grad_sum);
    }
}

// ============================================================
// Stage 3 Main Function
// ============================================================
void stage3_blend(
    grad_t        grad_c, grad_t grad_u, grad_t grad_d,
    grad_t        grad_l, grad_t grad_r,
    avg_value_t   avg0_c, avg_value_t avg0_u, avg_value_t avg0_d,
    avg_value_t   avg0_l, avg_value_t avg0_r,
    avg_value_t   avg1_c, avg_value_t avg1_u, avg_value_t avg1_d,
    avg_value_t   avg1_l, avg_value_t avg1_r,
    blend_grad_t  &blend0_grad,
    blend_grad_t  &blend1_grad
) {
    #pragma HLS INLINE

    // Sort gradients for reference
    grad_t sorted_g0, sorted_g1, sorted_g2, sorted_g3, sorted_g4;
    sort5_inverse(grad_u, grad_d, grad_l, grad_r, grad_c,
                  sorted_g0, sorted_g1, sorted_g2, sorted_g3, sorted_g4);

    // Compute blend0_grad
    compute_blend_gradient(
        avg0_c, avg0_u, avg0_d, avg0_l, avg0_r,
        grad_c, grad_u, grad_d, grad_l, grad_r,
        blend0_grad
    );

    // Compute blend1_grad
    compute_blend_gradient(
        avg1_c, avg1_u, avg1_d, avg1_l, avg1_r,
        grad_c, grad_u, grad_d, grad_l, grad_r,
        blend1_grad
    );
}
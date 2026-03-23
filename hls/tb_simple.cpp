// ============================================================
// ISP-CSIIR Simplified HLS Test Bench with Intermediate Output
// Fixed version matching Python golden model
// ============================================================

#include <iostream>
#include <fstream>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <string>
#include <algorithm>

// ============================================================
// Type Definitions
// ============================================================
typedef uint16_t pixel_u10_t;
typedef int16_t pixel_s11_t;
typedef uint16_t grad_t;
typedef uint8_t win_size_t;
typedef int16_t avg_value_t;
typedef int16_t blend_grad_t;

const int MAX_PIXEL = 1023;
const int RATIO_SCALE = 64;

// Default configuration
const uint8_t DEFAULT_WIN_THRESH[4] = {16, 24, 32, 40};
const uint8_t DEFAULT_GRAD_CLIP[4] = {15, 23, 31, 39};

// ============================================================
// Kernels (matching Python model exactly)
// ============================================================
const uint8_t AVG_FACTOR_2x2[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 1, 2, 1, 0},
    {0, 2, 4, 2, 0},
    {0, 1, 2, 1, 0},
    {0, 0, 0, 0, 0}
};

const uint8_t AVG_FACTOR_3x3[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 1, 1, 1, 0},
    {0, 1, 1, 1, 0},
    {0, 1, 1, 1, 0},
    {0, 0, 0, 0, 0}
};

const uint8_t AVG_FACTOR_4x4[5][5] = {
    {1, 1, 2, 1, 1},
    {1, 2, 4, 2, 1},
    {2, 4, 8, 4, 2},
    {1, 2, 4, 2, 1},
    {1, 1, 2, 1, 1}
};

const uint8_t AVG_FACTOR_5x5[5][5] = {
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1}
};

// Direction masks
const uint8_t MASK_U[5][5] = {
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0}
};

const uint8_t MASK_D[5][5] = {
    {0, 0, 0, 0, 0},
    {0, 0, 0, 0, 0},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1}
};

const uint8_t MASK_L[5][5] = {
    {1, 1, 1, 0, 0},
    {1, 1, 1, 0, 0},
    {1, 1, 1, 0, 0},
    {1, 1, 1, 0, 0},
    {1, 1, 1, 0, 0}
};

const uint8_t MASK_R[5][5] = {
    {0, 0, 1, 1, 1},
    {0, 0, 1, 1, 1},
    {0, 0, 1, 1, 1},
    {0, 0, 1, 1, 1},
    {0, 0, 1, 1, 1}
};

// All-ones mask
const uint8_t MASK_ALL[5][5] = {
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1}
};

// Inverse table
const uint32_t INV_TABLE[65] = {
    0, 65536, 32768, 21845, 16384, 13107, 10923, 9362, 8192, 7282, 6554,
    5958, 5461, 5041, 4681, 4369, 4096, 3855, 3641, 3449, 3277,
    3120, 2979, 2849, 2731, 2621, 2521, 2427, 2341, 2259, 2185,
    2115, 2048, 1986, 1928, 1872, 1820, 1771, 1725, 1680, 1638,
    1598, 1560, 1524, 1489, 1456, 1425, 1394, 1365, 1338, 1311,
    1286, 1261, 1238, 1215, 1193, 1172, 1151, 1132, 1113, 1094,
    1076, 1059, 1042, 1024
};

// ============================================================
// Division Utilities
// ============================================================
uint16_t div_by_5(uint16_t grad_abs) {
    return ((uint32_t)grad_abs * 205) >> 10;
}

int16_t div_by_lookup(int32_t numerator, uint32_t denominator) {
    if (denominator == 0) return 0;
    bool neg = numerator < 0;
    uint32_t abs_num = neg ? -numerator : numerator;
    uint32_t inv = INV_TABLE[denominator > 64 ? 64 : denominator];
    uint32_t result = (abs_num * inv) >> 16;
    return neg ? -(int16_t)result : (int16_t)result;
}

int16_t div_by_nr(int64_t numerator, uint32_t denominator) {
    if (denominator == 0 || numerator == 0) return 0;
    bool neg = numerator < 0;
    uint64_t abs_num = neg ? -numerator : numerator;

    // For initial reciprocal estimate:
    // Python: msb_pos = denominator.bit_length() - 1
    // x0 = 1 << (16 - msb_pos)
    // We need to find the position of the MSB (0-indexed from LSB)
    int msb_pos = 0;
    uint32_t temp = denominator;
    while (temp >>= 1) msb_pos++;  // Find MSB position
    uint32_t x0 = (denominator <= 64) ? INV_TABLE[denominator] : (1u << (16 - msb_pos));
    uint64_t prod = (uint64_t)denominator * x0;
    int64_t two_minus = (2LL << 16) - (int64_t)prod;
    uint32_t x1 = ((uint64_t)x0 * two_minus) >> 16;
    prod = (uint64_t)denominator * x1;
    two_minus = (2LL << 16) - (int64_t)prod;
    uint32_t x2 = ((uint64_t)x1 * two_minus) >> 16;

    uint32_t result = (abs_num * x2) >> 16;
    if (result > 511) result = 511;
    return neg ? -(int16_t)result : (int16_t)result;
}

// ============================================================
// Intermediate Data Structures
// ============================================================
struct Stage1Data {
    int grad;
    int win_size;
    int grad_h;
    int grad_v;
};

struct Stage2Data {
    int avg0_c, avg0_u, avg0_d, avg0_l, avg0_r;
    int avg1_c, avg1_u, avg1_d, avg1_l, avg1_r;
};

struct Stage3Data {
    int blend0_grad;
    int blend1_grad;
};

// ============================================================
// Processing Functions (Matching Python Model)
// ============================================================

void stage1_gradient(pixel_u10_t window[5][5], Stage1Data &s1, const uint8_t grad_clip[4]) {
    int32_t grad_h = 0, grad_v = 0;
    for (int i = 0; i < 5; i++) {
        grad_h += (int32_t)window[0][i] - (int32_t)window[4][i];
        grad_v += (int32_t)window[i][0] - (int32_t)window[i][4];
    }

    uint16_t grad_h_abs = (grad_h < 0) ? -grad_h : grad_h;
    uint16_t grad_v_abs = (grad_v < 0) ? -grad_v : grad_v;

    s1.grad_h = grad_h;
    s1.grad_v = grad_v;
    s1.grad = div_by_5(grad_h_abs) + div_by_5(grad_v_abs);

    if (s1.grad <= grad_clip[0]) s1.win_size = 16;
    else if (s1.grad <= grad_clip[1]) s1.win_size = 23;
    else if (s1.grad <= grad_clip[2]) s1.win_size = 31;
    else if (s1.grad <= grad_clip[3]) s1.win_size = 39;
    else s1.win_size = 40;
}

// Helper: compute directional average matching Python's compute_directional_average
int16_t compute_directional_average(pixel_s11_t src_s11[5][5], const uint8_t factor[5][5], const uint8_t mask[5][5]) {
    int32_t weighted_sum = 0;
    int sum_factor = 0;

    for (int i = 0; i < 5; i++) {
        for (int j = 0; j < 5; j++) {
            uint8_t masked_factor = factor[i][j] * mask[i][j];
            weighted_sum += src_s11[i][j] * masked_factor;
            sum_factor += masked_factor;
        }
    }

    if (sum_factor == 0) return 0;
    return div_by_lookup(weighted_sum, sum_factor);
}

void stage2_average(pixel_s11_t src_s11[5][5], win_size_t win_size, const uint8_t win_thresh[4], Stage2Data &s2) {
    // Select kernels based on window size (matching Python logic)
    const uint8_t (*avg0_factor)[5];
    const uint8_t (*avg1_factor)[5];

    static const uint8_t zeros[5][5] = {{0,0,0,0,0}, {0,0,0,0,0}, {0,0,0,0,0}, {0,0,0,0,0}, {0,0,0,0,0}};

    if (win_size < win_thresh[0]) {
        avg0_factor = zeros;
        avg1_factor = AVG_FACTOR_2x2;
    } else if (win_size < win_thresh[1]) {
        avg0_factor = AVG_FACTOR_2x2;
        avg1_factor = AVG_FACTOR_3x3;
    } else if (win_size < win_thresh[2]) {
        avg0_factor = AVG_FACTOR_3x3;
        avg1_factor = AVG_FACTOR_4x4;
    } else if (win_size < win_thresh[3]) {
        avg0_factor = AVG_FACTOR_4x4;
        avg1_factor = AVG_FACTOR_5x5;
    } else {
        avg0_factor = AVG_FACTOR_5x5;
        avg1_factor = zeros;
    }

    // Compute avg0 values (matching Python: center uses MASK_ALL, others use direction masks)
    s2.avg0_c = compute_directional_average(src_s11, avg0_factor, MASK_ALL);
    s2.avg0_u = compute_directional_average(src_s11, avg0_factor, MASK_U);
    s2.avg0_d = compute_directional_average(src_s11, avg0_factor, MASK_D);
    s2.avg0_l = compute_directional_average(src_s11, avg0_factor, MASK_L);
    s2.avg0_r = compute_directional_average(src_s11, avg0_factor, MASK_R);

    // Compute avg1 values
    s2.avg1_c = compute_directional_average(src_s11, avg1_factor, MASK_ALL);
    s2.avg1_u = compute_directional_average(src_s11, avg1_factor, MASK_U);
    s2.avg1_d = compute_directional_average(src_s11, avg1_factor, MASK_D);
    s2.avg1_l = compute_directional_average(src_s11, avg1_factor, MASK_L);
    s2.avg1_r = compute_directional_average(src_s11, avg1_factor, MASK_R);
}

void stage3_blend(grad_t grad, const Stage2Data &s2, Stage3Data &s3) {
    // Python uses grad_center for all 5 directions
    // grad_sum = grad_c + grad_u + grad_d + grad_l + grad_r = 5 * grad
    uint32_t grad_sum = (uint32_t)grad * 5;

    if (grad_sum == 0) {
        // Equal weight average
        s3.blend0_grad = (s2.avg0_c + s2.avg0_u + s2.avg0_d + s2.avg0_l + s2.avg0_r) / 5;
        s3.blend1_grad = (s2.avg1_c + s2.avg1_u + s2.avg1_d + s2.avg1_l + s2.avg1_r) / 5;
    } else {
        // Gradient-weighted average
        // weighted_sum = avg_c * grad + avg_u * grad + ... = grad * (avg_c + avg_u + ...)
        int64_t sum_avg0 = (int64_t)s2.avg0_c + s2.avg0_u + s2.avg0_d + s2.avg0_l + s2.avg0_r;
        int64_t sum_avg1 = (int64_t)s2.avg1_c + s2.avg1_u + s2.avg1_d + s2.avg1_l + s2.avg1_r;

        int64_t weighted_sum0 = grad * sum_avg0;
        int64_t weighted_sum1 = grad * sum_avg1;

        s3.blend0_grad = div_by_nr(weighted_sum0, grad_sum);
        s3.blend1_grad = div_by_nr(weighted_sum1, grad_sum);
    }
}

pixel_u10_t stage4_output(const Stage3Data &s3, const Stage2Data &s2, win_size_t win_size,
                          const uint8_t win_thresh[4], const uint8_t blend_ratio[4]) {
    // Determine blend ratio index (matching Python)
    int ratio_idx = std::min(std::max((win_size >> 3) - 2, 0), 3);
    int ratio = blend_ratio[ratio_idx];

    // Horizontal blend (matching Python horizontal_blend function)
    // numerator = ratio * blend_grad + (64 - ratio) * avg_u
    // result = numerator >> 6
    int32_t blend0_hor = (ratio * s3.blend0_grad + (64 - ratio) * s2.avg0_u) >> 6;
    int32_t blend1_hor = (ratio * s3.blend1_grad + (64 - ratio) * s2.avg1_u) >> 6;

    // Determine final blend based on window size
    int16_t blend_uv;

    if (win_size < win_thresh[0]) {
        blend_uv = blend0_hor;
    } else if (win_size >= win_thresh[3]) {
        blend_uv = blend1_hor;
    } else {
        // Interpolate between blend0_hor and blend1_hor
        int win_remain = win_size & 0x7;  // win_size % 8
        blend_uv = (blend0_hor * win_remain + blend1_hor * (8 - win_remain)) >> 3;
    }

    // Convert to unsigned and clip
    int16_t output_signed = blend_uv + 512;
    if (output_signed < 0) output_signed = 0;
    if (output_signed > 1023) output_signed = 1023;

    return (pixel_u10_t)output_signed;
}

// ============================================================
// File I/O
// ============================================================
bool load_input(const std::string &fn, std::vector<uint16_t> &data, int sz) {
    std::ifstream ifs(fn);
    if (!ifs.is_open()) return false;
    data.clear();
    uint16_t v;
    while (ifs >> v && (int)data.size() < sz) data.push_back(v);
    return (int)data.size() == sz;
}

void save_stage1(const std::string &fn, const std::vector<Stage1Data> &d, int w) {
    std::ofstream ofs(fn);
    ofs << "# Stage 1: Gradient Computation Results\n";
    ofs << "# Format: row col grad win_size grad_h grad_v\n";
    for (size_t i = 0; i < d.size(); i++) {
        ofs << (i/w) << " " << (i%w) << " " << d[i].grad << " " << d[i].win_size
            << " " << d[i].grad_h << " " << d[i].grad_v << "\n";
    }
}

void save_stage2(const std::string &fn, const std::vector<Stage2Data> &d, int w) {
    std::ofstream ofs(fn);
    ofs << "# Stage 2: Multi-scale Directional Average Results\n";
    ofs << "# Format: row col avg0_c avg0_u avg0_d avg0_l avg0_r avg1_c avg1_u avg1_d avg1_l avg1_r\n";
    for (size_t i = 0; i < d.size(); i++) {
        ofs << (i/w) << " " << (i%w) << " " << d[i].avg0_c << " " << d[i].avg0_u << " " << d[i].avg0_d
            << " " << d[i].avg0_l << " " << d[i].avg0_r << " " << d[i].avg1_c << " " << d[i].avg1_u
            << " " << d[i].avg1_d << " " << d[i].avg1_l << " " << d[i].avg1_r << "\n";
    }
}

void save_stage3(const std::string &fn, const std::vector<Stage3Data> &d, int w) {
    std::ofstream ofs(fn);
    ofs << "# Stage 3: Gradient-weighted Directional Fusion Results\n";
    ofs << "# Format: row col blend0_grad blend1_grad\n";
    for (size_t i = 0; i < d.size(); i++) {
        ofs << (i/w) << " " << (i%w) << " " << d[i].blend0_grad << " " << d[i].blend1_grad << "\n";
    }
}

void save_output(const std::string &fn, const std::vector<uint16_t> &in, const std::vector<uint16_t> &out, int w) {
    std::ofstream ofs(fn);
    ofs << "# Stage 4: Final Output Results\n";
    ofs << "# Format: row col input_pixel output_pixel\n";
    for (size_t i = 0; i < out.size(); i++) {
        ofs << (i/w) << " " << (i%w) << " " << in[i] << " " << out[i] << "\n";
    }
}

// ============================================================
// Main
// ============================================================
int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "ISP-CSIIR HLS Test Bench (Fixed Version)" << std::endl;
    std::cout << "========================================" << std::endl;

    uint8_t win_thresh[4] = {16, 24, 32, 40};
    uint8_t grad_clip[4] = {15, 23, 31, 39};
    uint8_t blend_ratio[4] = {32, 32, 32, 32};

    struct Test { std::string name; int w, h; };
    Test tests[] = {
        {"flat", 64, 64}, {"gradient_h", 64, 64}, {"gradient_v", 64, 64},
        {"checkerboard", 64, 64}, {"edge", 64, 64}, {"center_peak", 64, 64},
        {"corner", 64, 64}, {"boundary", 64, 64}, {"random", 64, 64},
        {"edge_small", 16, 16}
    };

    system("mkdir -p ../verification/intermediate/hls");

    for (auto &t : tests) {
        std::cout << "\nProcessing: " << t.name << std::endl;
        std::string base = "../verification/test_vectors/input_" + t.name + ".txt";
        std::vector<uint16_t> input;
        if (!load_input(base, input, t.w * t.h)) { std::cout << "  Skip (not found)" << std::endl; continue; }

        std::vector<Stage1Data> s1_data(t.w * t.h);
        std::vector<Stage2Data> s2_data(t.w * t.h);
        std::vector<Stage3Data> s3_data(t.w * t.h);
        std::vector<uint16_t> output(t.w * t.h);

        for (int r = 0; r < t.h; r++) {
            for (int c = 0; c < t.w; c++) {
                int idx = r * t.w + c;

                // Get 5x5 window with boundary replication
                pixel_u10_t win[5][5];
                pixel_s11_t s11[5][5];
                for (int i = 0; i < 5; i++) {
                    for (int j = 0; j < 5; j++) {
                        int ri = std::max(0, std::min(r + i - 2, t.h - 1));
                        int ci = std::max(0, std::min(c + j - 2, t.w - 1));
                        win[i][j] = input[ri * t.w + ci];
                        s11[i][j] = (int16_t)win[i][j] - 512;
                    }
                }

                stage1_gradient(win, s1_data[idx], grad_clip);
                stage2_average(s11, s1_data[idx].win_size, win_thresh, s2_data[idx]);
                stage3_blend(s1_data[idx].grad, s2_data[idx], s3_data[idx]);
                output[idx] = stage4_output(s3_data[idx], s2_data[idx], s1_data[idx].win_size, win_thresh, blend_ratio);
            }
        }

        std::string out_base = "../verification/intermediate/hls/" + t.name;
        save_stage1(out_base + "_stage1.txt", s1_data, t.w);
        save_stage2(out_base + "_stage2.txt", s2_data, t.w);
        save_stage3(out_base + "_stage3.txt", s3_data, t.w);
        save_output(out_base + "_output.txt", input, output, t.w);

        uint16_t min_v = 1024, max_v = 0;
        for (auto v : output) { if (v < min_v) min_v = v; if (v > max_v) max_v = v; }
        std::cout << "  Output: [" << min_v << ", " << max_v << "]" << std::endl;
        std::cout << "  Saved intermediate data" << std::endl;
    }

    std::cout << "\n========================================" << std::endl;
    std::cout << "Run: python ../verification/scripts/compare_intermediate.py" << std::endl;
    std::cout << "========================================" << std::endl;

    return 0;
}
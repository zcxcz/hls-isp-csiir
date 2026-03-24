// ============================================================
// ISP-CSIIR Parameterized HLS Test Bench
// ============================================================
// Supports configurable input/output for random verification
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

const int MAX_PIXEL = 1023;

// Default configuration (can be overridden via command line)
static int WIN_THRESH[4] = {16, 24, 32, 40};
static int GRAD_CLIP[4] = {15, 23, 31, 39};
static int BLEND_RATIO[4] = {32, 32, 32, 32};
static int IMG_WIDTH = 64;
static int IMG_HEIGHT = 64;

// ============================================================
// Kernels
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

const uint8_t MASK_ALL[5][5] = {
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1},
    {1, 1, 1, 1, 1}
};

// ============================================================
// Inverse Table
// ============================================================
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

    int msb_pos = 0;
    uint32_t temp = denominator;
    while (temp >>= 1) msb_pos++;
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
// Processing Functions
// ============================================================
void stage1_gradient(pixel_u10_t window[5][5], int &grad, int &win_size, int &grad_h, int &grad_v) {
    int32_t gh = 0, gv = 0;
    for (int i = 0; i < 5; i++) {
        gh += (int32_t)window[0][i] - (int32_t)window[4][i];
        gv += (int32_t)window[i][0] - (int32_t)window[i][4];
    }

    grad_h = gh;
    grad_v = gv;

    uint16_t gh_abs = (gh < 0) ? -gh : gh;
    uint16_t gv_abs = (gv < 0) ? -gv : gv;
    grad = div_by_5(gh_abs) + div_by_5(gv_abs);

    if (grad <= GRAD_CLIP[0]) win_size = 16;
    else if (grad <= GRAD_CLIP[1]) win_size = 23;
    else if (grad <= GRAD_CLIP[2]) win_size = 31;
    else if (grad <= GRAD_CLIP[3]) win_size = 39;
    else win_size = 40;
}

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

void stage2_average(pixel_s11_t src_s11[5][5], int win_size,
                    int &avg0_c, int &avg0_u, int &avg0_d, int &avg0_l, int &avg0_r,
                    int &avg1_c, int &avg1_u, int &avg1_d, int &avg1_l, int &avg1_r) {
    static const uint8_t zeros[5][5] = {{0,0,0,0,0}, {0,0,0,0,0}, {0,0,0,0,0}, {0,0,0,0,0}, {0,0,0,0,0}};
    const uint8_t (*avg0_factor)[5];
    const uint8_t (*avg1_factor)[5];

    if (win_size < WIN_THRESH[0]) {
        avg0_factor = zeros;
        avg1_factor = AVG_FACTOR_2x2;
    } else if (win_size < WIN_THRESH[1]) {
        avg0_factor = AVG_FACTOR_2x2;
        avg1_factor = AVG_FACTOR_3x3;
    } else if (win_size < WIN_THRESH[2]) {
        avg0_factor = AVG_FACTOR_3x3;
        avg1_factor = AVG_FACTOR_4x4;
    } else if (win_size < WIN_THRESH[3]) {
        avg0_factor = AVG_FACTOR_4x4;
        avg1_factor = AVG_FACTOR_5x5;
    } else {
        avg0_factor = AVG_FACTOR_5x5;
        avg1_factor = zeros;
    }

    avg0_c = compute_directional_average(src_s11, avg0_factor, MASK_ALL);
    avg0_u = compute_directional_average(src_s11, avg0_factor, MASK_U);
    avg0_d = compute_directional_average(src_s11, avg0_factor, MASK_D);
    avg0_l = compute_directional_average(src_s11, avg0_factor, MASK_L);
    avg0_r = compute_directional_average(src_s11, avg0_factor, MASK_R);

    avg1_c = compute_directional_average(src_s11, avg1_factor, MASK_ALL);
    avg1_u = compute_directional_average(src_s11, avg1_factor, MASK_U);
    avg1_d = compute_directional_average(src_s11, avg1_factor, MASK_D);
    avg1_l = compute_directional_average(src_s11, avg1_factor, MASK_L);
    avg1_r = compute_directional_average(src_s11, avg1_factor, MASK_R);
}

// Helper: Get gradient with boundary replication
int get_grad_with_boundary(const std::vector<int> &grad_map, int row, int col, int h, int w) {
    int r = std::max(0, std::min(row, h - 1));
    int c = std::max(0, std::min(col, w - 1));
    return grad_map[r * w + c];
}

// Updated: Use 5-direction gradients
void stage3_blend_5dir(int grad_c, int grad_u, int grad_d, int grad_l, int grad_r,
                       int avg0_c, int avg0_u, int avg0_d, int avg0_l, int avg0_r,
                       int avg1_c, int avg1_u, int avg1_d, int avg1_l, int avg1_r,
                       int &blend0_grad, int &blend1_grad) {
    // Compute gradient sum using 5 different gradients
    uint32_t grad_sum = (uint32_t)grad_c + (uint32_t)grad_u + (uint32_t)grad_d +
                        (uint32_t)grad_l + (uint32_t)grad_r;

    if (grad_sum == 0) {
        // Equal weight average
        blend0_grad = (avg0_c + avg0_u + avg0_d + avg0_l + avg0_r) / 5;
        blend1_grad = (avg1_c + avg1_u + avg1_d + avg1_l + avg1_r) / 5;
    } else {
        // Gradient-weighted average with 5 different gradient values
        int64_t weighted_sum0 = (int64_t)avg0_c * grad_c + (int64_t)avg0_u * grad_u +
                                (int64_t)avg0_d * grad_d + (int64_t)avg0_l * grad_l +
                                (int64_t)avg0_r * grad_r;
        int64_t weighted_sum1 = (int64_t)avg1_c * grad_c + (int64_t)avg1_u * grad_u +
                                (int64_t)avg1_d * grad_d + (int64_t)avg1_l * grad_l +
                                (int64_t)avg1_r * grad_r;

        blend0_grad = div_by_nr(weighted_sum0, grad_sum);
        blend1_grad = div_by_nr(weighted_sum1, grad_sum);
    }
}

pixel_u10_t stage4_output(int blend0_grad, int blend1_grad,
                          int avg0_u, int avg1_u, int win_size) {
    int ratio_idx = std::min(std::max((win_size >> 3) - 2, 0), 3);
    int ratio = BLEND_RATIO[ratio_idx];

    int32_t blend0_hor = (ratio * blend0_grad + (64 - ratio) * avg0_u) >> 6;
    int32_t blend1_hor = (ratio * blend1_grad + (64 - ratio) * avg1_u) >> 6;

    int16_t blend_uv;
    if (win_size < WIN_THRESH[0]) {
        blend_uv = blend0_hor;
    } else if (win_size >= WIN_THRESH[3]) {
        blend_uv = blend1_hor;
    } else {
        int win_remain = win_size & 0x7;
        blend_uv = (blend0_hor * win_remain + blend1_hor * (8 - win_remain)) >> 3;
    }

    int16_t output_signed = blend_uv + 512;
    if (output_signed < 0) output_signed = 0;
    if (output_signed > 1023) output_signed = 1023;
    return (pixel_u10_t)output_signed;
}

// ============================================================
// File I/O
// ============================================================
bool load_input(const std::string &fn, std::vector<uint16_t> &data) {
    std::ifstream ifs(fn);
    if (!ifs.is_open()) return false;
    data.clear();
    uint16_t v;
    while (ifs >> v) data.push_back(v);
    return !data.empty();
}

bool load_config(const std::string &fn) {
    std::ifstream ifs(fn);
    if (!ifs.is_open()) return false;

    std::string key;
    while (ifs >> key) {
        if (key == "width") {
            ifs >> IMG_WIDTH;
        } else if (key == "height") {
            ifs >> IMG_HEIGHT;
        } else if (key == "win_thresh") {
            ifs >> WIN_THRESH[0] >> WIN_THRESH[1] >> WIN_THRESH[2] >> WIN_THRESH[3];
        } else if (key == "grad_clip") {
            ifs >> GRAD_CLIP[0] >> GRAD_CLIP[1] >> GRAD_CLIP[2] >> GRAD_CLIP[3];
        } else if (key == "blend_ratio") {
            ifs >> BLEND_RATIO[0] >> BLEND_RATIO[1] >> BLEND_RATIO[2] >> BLEND_RATIO[3];
        }
    }
    return true;
}

// ============================================================
// Main
// ============================================================
void print_usage(const char *prog) {
    std::cerr << "Usage: " << prog << " <input_file> <output_dir> [config_file]" << std::endl;
    std::cerr << std::endl;
    std::cerr << "Arguments:" << std::endl;
    std::cerr << "  input_file   : Path to input pixel file (one value per line)" << std::endl;
    std::cerr << "  output_dir   : Directory to save intermediate results" << std::endl;
    std::cerr << "  config_file  : Optional configuration file" << std::endl;
    std::cerr << std::endl;
    std::cerr << "Config file format (key-value pairs):" << std::endl;
    std::cerr << "  width W" << std::endl;
    std::cerr << "  height H" << std::endl;
    std::cerr << "  win_thresh t0 t1 t2 t3" << std::endl;
    std::cerr << "  grad_clip g0 g1 g2 g3" << std::endl;
    std::cerr << "  blend_ratio b0 b1 b2 b3" << std::endl;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        print_usage(argv[0]);
        return 1;
    }

    std::string input_file = argv[1];
    std::string output_dir = argv[2];
    std::string config_file = (argc > 3) ? argv[3] : "";

    // Load configuration if provided
    if (!config_file.empty()) {
        if (!load_config(config_file)) {
            std::cerr << "Warning: Could not load config file, using defaults" << std::endl;
        }
    }

    // Load input
    std::vector<uint16_t> input;
    if (!load_input(input_file, input)) {
        std::cerr << "Error: Could not load input file: " << input_file << std::endl;
        return 1;
    }

    // Use dimensions from config file
    int width = IMG_WIDTH;
    int height = IMG_HEIGHT;
    int total_pixels = input.size();

    // Verify dimensions
    if (width * height != total_pixels) {
        std::cerr << "Warning: Config dimensions " << width << "x" << height << " don't match input size " << total_pixels << std::endl;
        // Try to infer dimensions
        int sq = (int)std::sqrt(total_pixels);
        if (sq * sq == total_pixels) {
            width = height = sq;
        } else {
            std::cerr << "Error: Cannot determine image dimensions" << std::endl;
            return 1;
        }
    }

    std::cout << "Processing: " << width << "x" << height << " image (" << total_pixels << " pixels)" << std::endl;

    // Process
    std::vector<int> s1_grad(total_pixels), s1_win_size(total_pixels);
    std::vector<int> s1_grad_h(total_pixels), s1_grad_v(total_pixels);
    std::vector<int> s2_avg0_c(total_pixels), s2_avg0_u(total_pixels), s2_avg0_d(total_pixels);
    std::vector<int> s2_avg0_l(total_pixels), s2_avg0_r(total_pixels);
    std::vector<int> s2_avg1_c(total_pixels), s2_avg1_u(total_pixels), s2_avg1_d(total_pixels);
    std::vector<int> s2_avg1_l(total_pixels), s2_avg1_r(total_pixels);
    std::vector<int> s3_blend0(total_pixels), s3_blend1(total_pixels);
    std::vector<uint16_t> output(total_pixels);

    // Step 1: Pre-compute gradient map (like Python model)
    std::vector<int> grad_map(total_pixels);
    for (int r = 0; r < height; r++) {
        for (int c = 0; c < width; c++) {
            pixel_u10_t win[5][5];
            for (int i = 0; i < 5; i++) {
                for (int j = 0; j < 5; j++) {
                    int ri = std::max(0, std::min(r + i - 2, height - 1));
                    int ci = std::max(0, std::min(c + j - 2, width - 1));
                    win[i][j] = input[ri * width + ci];
                }
            }
            int grad, win_size, grad_h, grad_v;
            stage1_gradient(win, grad, win_size, grad_h, grad_v);
            grad_map[r * width + c] = grad;
        }
    }

    // Step 2: Process with 5-direction gradients
    for (int r = 0; r < height; r++) {
        for (int c = 0; c < width; c++) {
            int idx = r * width + c;

            // Get 5x5 window
            pixel_u10_t win[5][5];
            pixel_s11_t s11[5][5];
            for (int i = 0; i < 5; i++) {
                for (int j = 0; j < 5; j++) {
                    int ri = std::max(0, std::min(r + i - 2, height - 1));
                    int ci = std::max(0, std::min(c + j - 2, width - 1));
                    win[i][j] = input[ri * width + ci];
                    s11[i][j] = (int16_t)win[i][j] - 512;
                }
            }

            // Stage 1
            stage1_gradient(win, s1_grad[idx], s1_win_size[idx], s1_grad_h[idx], s1_grad_v[idx]);

            // Stage 2
            stage2_average(s11, s1_win_size[idx],
                          s2_avg0_c[idx], s2_avg0_u[idx], s2_avg0_d[idx], s2_avg0_l[idx], s2_avg0_r[idx],
                          s2_avg1_c[idx], s2_avg1_u[idx], s2_avg1_d[idx], s2_avg1_l[idx], s2_avg1_r[idx]);

            // Stage 3: Use 5-direction gradients from gradient map
            int grad_c = get_grad_with_boundary(grad_map, r, c, height, width);
            int grad_u = get_grad_with_boundary(grad_map, r - 1, c, height, width);
            int grad_d = get_grad_with_boundary(grad_map, r + 1, c, height, width);
            int grad_l = get_grad_with_boundary(grad_map, r, c - 1, height, width);
            int grad_r = get_grad_with_boundary(grad_map, r, c + 1, height, width);

            stage3_blend_5dir(grad_c, grad_u, grad_d, grad_l, grad_r,
                             s2_avg0_c[idx], s2_avg0_u[idx], s2_avg0_d[idx], s2_avg0_l[idx], s2_avg0_r[idx],
                             s2_avg1_c[idx], s2_avg1_u[idx], s2_avg1_d[idx], s2_avg1_l[idx], s2_avg1_r[idx],
                             s3_blend0[idx], s3_blend1[idx]);

            // Stage 4
            output[idx] = stage4_output(s3_blend0[idx], s3_blend1[idx],
                                       s2_avg0_u[idx], s2_avg1_u[idx], s1_win_size[idx]);
        }
    }

    // Save results
    system(("mkdir -p " + output_dir).c_str());

    auto save_stage1 = [&](const std::string &fn) {
        std::ofstream ofs(fn);
        ofs << "# Stage 1: Gradient Computation Results\n";
        ofs << "# Format: row col grad win_size grad_h grad_v\n";
        for (int i = 0; i < total_pixels; i++) {
            ofs << (i/width) << " " << (i%width) << " " << s1_grad[i] << " " << s1_win_size[i]
                << " " << s1_grad_h[i] << " " << s1_grad_v[i] << "\n";
        }
    };

    auto save_stage2 = [&](const std::string &fn) {
        std::ofstream ofs(fn);
        ofs << "# Stage 2: Multi-scale Directional Average Results\n";
        ofs << "# Format: row col avg0_c avg0_u avg0_d avg0_l avg0_r avg1_c avg1_u avg1_d avg1_l avg1_r\n";
        for (int i = 0; i < total_pixels; i++) {
            ofs << (i/width) << " " << (i%width) << " "
                << s2_avg0_c[i] << " " << s2_avg0_u[i] << " " << s2_avg0_d[i]
                << " " << s2_avg0_l[i] << " " << s2_avg0_r[i] << " "
                << s2_avg1_c[i] << " " << s2_avg1_u[i] << " " << s2_avg1_d[i]
                << " " << s2_avg1_l[i] << " " << s2_avg1_r[i] << "\n";
        }
    };

    auto save_stage3 = [&](const std::string &fn) {
        std::ofstream ofs(fn);
        ofs << "# Stage 3: Gradient-weighted Directional Fusion Results\n";
        ofs << "# Format: row col blend0_grad blend1_grad\n";
        for (int i = 0; i < total_pixels; i++) {
            ofs << (i/width) << " " << (i%width) << " " << s3_blend0[i] << " " << s3_blend1[i] << "\n";
        }
    };

    auto save_output = [&](const std::string &fn) {
        std::ofstream ofs(fn);
        ofs << "# Stage 4: Final Output Results\n";
        ofs << "# Format: row col input_pixel output_pixel\n";
        for (int i = 0; i < total_pixels; i++) {
            ofs << (i/width) << " " << (i%width) << " " << input[i] << " " << output[i] << "\n";
        }
    };

    save_stage1(output_dir + "/stage1.txt");
    save_stage2(output_dir + "/stage2.txt");
    save_stage3(output_dir + "/stage3.txt");
    save_output(output_dir + "/output.txt");

    std::cout << "Results saved to: " << output_dir << std::endl;

    return 0;
}
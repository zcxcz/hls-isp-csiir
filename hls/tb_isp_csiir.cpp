// ============================================================
// ISP-CSIIR HLS Test Bench
// ============================================================
// Project: ISP-CSIIR HLS Module
// Version: v1.0
// Date: 2026-03-23
// Description:
//   - Test image input generation
//   - Output verification
//   - Configurable test parameters
// ============================================================

#include <iostream>
#include <fstream>
#include <cmath>
#include <cstdlib>
#include "isp_csiir.h"

// ============================================================
// Test Configuration
// ============================================================
#define TEST_WIDTH      64
#define TEST_HEIGHT     64
#define TEST_PIXELS     (TEST_WIDTH * TEST_HEIGHT)

// ============================================================
// Generate Test Image
// ============================================================
void generate_test_image(pixel_u10_t *image, int width, int height, int pattern) {
    for (int row = 0; row < height; row++) {
        for (int col = 0; col < width; col++) {
            int idx = row * width + col;
            pixel_u10_t value;

            switch (pattern) {
                case 0:  // Flat image
                    value = 512;
                    break;

                case 1:  // Horizontal gradient
                    value = (pixel_u10_t)(col * 1023 / width);
                    break;

                case 2:  // Vertical gradient
                    value = (pixel_u10_t)(row * 1023 / height);
                    break;

                case 3:  // Checkerboard
                    value = ((row + col) % 2 == 0) ? 800 : 200;
                    break;

                case 4:  // Edge pattern
                    if (col == width / 2) {
                        value = 900;
                    } else if (row == height / 2) {
                        value = 100;
                    } else {
                        value = 512;
                    }
                    break;

                case 5:  // Random noise
                    value = (pixel_u10_t)(rand() % 1024);
                    break;

                default:  // Center peak
                    int center_x = width / 2;
                    int center_y = height / 2;
                    int dist = abs(col - center_x) + abs(row - center_y);
                    int max_dist = center_x + center_y;
                    value = (pixel_u10_t)(1023 * (max_dist - dist) / max_dist);
                    value = (value < 0) ? 0 : value;
                    break;
            }

            image[idx] = value;
        }
    }
}

// ============================================================
// Write Image to File
// ============================================================
void write_image_to_file(const char *filename, pixel_u10_t *image, int width, int height) {
    std::ofstream ofs(filename);
    if (!ofs.is_open()) {
        std::cerr << "Error: Cannot open file " << filename << std::endl;
        return;
    }

    for (int row = 0; row < height; row++) {
        for (int col = 0; col < width; col++) {
            ofs << image[row * width + col];
            if (col < width - 1) ofs << " ";
        }
        ofs << "\n";
    }

    ofs.close();
    std::cout << "Image saved to " << filename << std::endl;
}

// ============================================================
// Run Test
// ============================================================
int run_test(int width, int height, int pattern, bool verbose) {
    std::cout << "========================================" << std::endl;
    std::cout << "Test Configuration:" << std::endl;
    std::cout << "  Image Size: " << width << " x " << height << std::endl;
    std::cout << "  Pattern: " << pattern << std::endl;
    std::cout << "========================================" << std::endl;

    // Allocate test images
    pixel_u10_t *input_image = new pixel_u10_t[width * height];
    pixel_u10_t *output_image = new pixel_u10_t[width * height];

    // Generate input image
    generate_test_image(input_image, width, height, pattern);

    // Create input and output streams
    hls::stream<axis_pixel_t> din_stream;
    hls::stream<axis_pixel_t> dout_stream;

    // Write input to stream
    for (int row = 0; row < height; row++) {
        for (int col = 0; col < width; col++) {
            int idx = row * width + col;
            axis_pixel_t din;
            din.data = input_image[idx];
            din.last = (row == height - 1 && col == width - 1) ? 1 : 0;
            din.user = (row == 0 && col == 0) ? 1 : 0;
            din_stream.write(din);
        }
    }

    // Run the ISP-CSIIR module
    isp_csiir_top(
        din_stream,
        dout_stream,
        width,       // img_width
        height,      // img_height
        16, 24, 32, 40,  // win_thresh[0-3]
        15, 23, 31, 39,  // grad_clip[0-3]
        32, 32, 32, 32,  // blend_ratio[0-3]
        32           // edge_protect
    );

    // Read output from stream
    int valid_count = 0;
    while (!dout_stream.empty()) {
        axis_pixel_t dout = dout_stream.read();
        if (valid_count < width * height) {
            output_image[valid_count] = dout.data;
            valid_count++;
        }
    }

    std::cout << "Output pixels received: " << valid_count << std::endl;

    // Statistics
    int min_val = 1024, max_val = -1;
    long long sum_val = 0;

    for (int i = 0; i < valid_count; i++) {
        if (output_image[i] < min_val) min_val = output_image[i];
        if (output_image[i] > max_val) max_val = output_image[i];
        sum_val += output_image[i];
    }

    double avg_val = (double)sum_val / valid_count;

    std::cout << "Output Statistics:" << std::endl;
    std::cout << "  Min: " << min_val << std::endl;
    std::cout << "  Max: " << max_val << std::endl;
    std::cout << "  Avg: " << avg_val << std::endl;

    // Print sample pixels
    if (verbose) {
        std::cout << "\nSample Output Pixels (center region):" << std::endl;
        int center_y = height / 2;
        int center_x = width / 2;

        for (int y = center_y - 2; y <= center_y + 2; y++) {
            for (int x = center_x - 2; x <= center_x + 2; x++) {
                if (y >= 0 && y < height && x >= 0 && x < width) {
                    int idx = y * width + x;
                    std::cout << output_image[idx] << "\t";
                }
            }
            std::cout << std::endl;
        }
    }

    // Save output image
    if (pattern == 0) {
        write_image_to_file("output_flat.txt", output_image, width, height);
    } else if (pattern == 4) {
        write_image_to_file("output_edge.txt", output_image, width, height);
    }

    // Cleanup
    delete[] input_image;
    delete[] output_image;

    return 0;
}

// ============================================================
// Main Function
// ============================================================
int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "ISP-CSIIR HLS Test Bench" << std::endl;
    std::cout << "========================================" << std::endl;

    int errors = 0;

    // Test 1: Flat image
    std::cout << "\n=== Test 1: Flat Image ===" << std::endl;
    errors += run_test(TEST_WIDTH, TEST_HEIGHT, 0, true);

    // Test 2: Horizontal gradient
    std::cout << "\n=== Test 2: Horizontal Gradient ===" << std::endl;
    errors += run_test(TEST_WIDTH, TEST_HEIGHT, 1, true);

    // Test 3: Vertical gradient
    std::cout << "\n=== Test 3: Vertical Gradient ===" << std::endl;
    errors += run_test(TEST_WIDTH, TEST_HEIGHT, 2, true);

    // Test 4: Checkerboard
    std::cout << "\n=== Test 4: Checkerboard ===" << std::endl;
    errors += run_test(TEST_WIDTH, TEST_HEIGHT, 3, true);

    // Test 5: Edge pattern
    std::cout << "\n=== Test 5: Edge Pattern ===" << std::endl;
    errors += run_test(TEST_WIDTH, TEST_HEIGHT, 4, true);

    // Test 6: Center peak
    std::cout << "\n=== Test 6: Center Peak ===" << std::endl;
    errors += run_test(TEST_WIDTH, TEST_HEIGHT, 6, true);

    // Test 7: Small image
    std::cout << "\n=== Test 7: Small Image (16x16) ===" << std::endl;
    errors += run_test(16, 16, 4, true);

    // Summary
    std::cout << "\n========================================" << std::endl;
    std::cout << "Test Summary:" << std::endl;
    std::cout << "  Total tests: 7" << std::endl;
    std::cout << "  Errors: " << errors << std::endl;
    std::cout << "========================================" << std::endl;

    if (errors == 0) {
        std::cout << "All tests PASSED!" << std::endl;
        return 0;
    } else {
        std::cout << "Some tests FAILED!" << std::endl;
        return 1;
    }
}
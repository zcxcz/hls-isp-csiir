// ============================================================
// ISP-CSIIR HLS Coverage Test Bench
// ============================================================
// Testbench that calls isp_csiir_top for code coverage collection
// Date: 2026-03-25
// ============================================================

#include <iostream>
#include <fstream>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <vector>
#include <string>
#include <algorithm>

#include "isp_csiir.h"

// Default configuration
static int WIN_THRESH[4] = {16, 24, 32, 40};
static int GRAD_CLIP[4] = {15, 23, 31, 39};
static int BLEND_RATIO[4] = {32, 32, 32, 32};
static int IMG_WIDTH = 64;
static int IMG_HEIGHT = 64;
static int EDGE_PROTECT = 32;

// ============================================================
// Helper Functions
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
        } else if (key == "edge_protect") {
            ifs >> EDGE_PROTECT;
        }
    }
    return true;
}

void save_output(const std::string &fn, const std::vector<uint16_t> &data) {
    std::ofstream ofs(fn);
    for (auto v : data) {
        ofs << v << "\n";
    }
}

// ============================================================
// Main
// ============================================================
void print_usage(const char *prog) {
    std::cerr << "Usage: " << prog << " <input_file> <output_dir> [config_file]" << std::endl;
    std::cerr << std::endl;
    std::cerr << "Arguments:" << std::endl;
    std::cerr << "  input_file   : Path to input pixel file (one value per line)" << std::endl;
    std::cerr << "  output_dir   : Directory to save output" << std::endl;
    std::cerr << "  config_file  : Optional configuration file" << std::endl;
    std::cerr << std::endl;
    std::cerr << "Config file format (text):" << std::endl;
    std::cerr << "  width <value>" << std::endl;
    std::cerr << "  height <value>" << std::endl;
    std::cerr << "  win_thresh <t0> <t1> <t2> <t3>" << std::endl;
    std::cerr << "  grad_clip <g0> <g1> <g2> <g3>" << std::endl;
    std::cerr << "  blend_ratio <r0> <r1> <r2> <r3>" << std::endl;
    std::cerr << "  edge_protect <value>" << std::endl;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        print_usage(argv[0]);
        return 1;
    }

    std::string input_file = argv[1];
    std::string output_dir = argv[2];
    std::string config_file = (argc > 3) ? argv[3] : "";

    // Load config if provided
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

    int width = IMG_WIDTH;
    int height = IMG_HEIGHT;
    int total_pixels = input.size();

    // Verify dimensions
    if (width * height != total_pixels) {
        std::cerr << "Warning: Config dimensions " << width << "x" << height << " don't match input size " << total_pixels << std::endl;
        int sq = (int)std::sqrt(total_pixels);
        if (sq * sq == total_pixels) {
            width = height = sq;
        } else {
            std::cerr << "Error: Cannot determine image dimensions" << std::endl;
            return 1;
        }
    }

    std::cout << "Processing: " << width << "x" << height << " image (" << total_pixels << " pixels)" << std::endl;

    // Create AXI-Stream input and output
    hls::stream<axis_pixel_t> din_stream("din_stream");
    hls::stream<axis_pixel_t> dout_stream("dout_stream");

    // Fill input stream
    for (int i = 0; i < total_pixels; i++) {
        axis_pixel_t pixel;
        pixel.data = input[i];
        pixel.last = (i == total_pixels - 1) ? 1 : 0;
        pixel.user = (i == 0) ? 1 : 0;  // SOF indicator
        din_stream.write(pixel);
    }

    // Call the HLS top function
    isp_csiir_top(
        din_stream,
        dout_stream,
        width,
        height,
        WIN_THRESH[0], WIN_THRESH[1], WIN_THRESH[2], WIN_THRESH[3],
        GRAD_CLIP[0], GRAD_CLIP[1], GRAD_CLIP[2], GRAD_CLIP[3],
        BLEND_RATIO[0], BLEND_RATIO[1], BLEND_RATIO[2], BLEND_RATIO[3],
        EDGE_PROTECT
    );

    // Read output stream
    std::vector<uint16_t> output;
    while (!dout_stream.empty()) {
        axis_pixel_t pixel = dout_stream.read();
        output.push_back((uint16_t)(int)pixel.data);
    }

    // Save output
    std::string output_file = output_dir + "/output.txt";
    save_output(output_file, output);

    std::cout << "Results saved to: " << output_dir << std::endl;

    return 0;
}
# ISP-CSIIR 测试平台增强建议

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | ISP-CSIIR HLS 模块 |
| 项目编号 | prj_0 |
| 文档版本 | v1.0 |
| 创建日期 | 2026-03-23 |
| 作者 | rtl-verf |
| 状态 | 待评审 |

---

## 1. 现有测试平台分析

### 1.1 当前测试平台结构

**文件位置:** `/home/sheldon/hls_project/isp-csiir/hls/tb_isp_csiir.cpp`

**当前功能:**
- 7 种测试模式生成
- AXI-Stream 数据接口测试
- 基本统计输出
- 可选文件输出

### 1.2 当前测试用例

| 测试编号 | 模式 | 描述 | 验证内容 |
|----------|------|------|----------|
| Test 1 | 平坦图像 | 全 512 像素 | 基准输出 |
| Test 2 | 水平梯度 | 水平变化 | 梯度计算 |
| Test 3 | 垂直梯度 | 垂直变化 | 梯度计算 |
| Test 4 | 棋盘格 | 交替值 | 边缘响应 |
| Test 5 | 边缘图案 | 十字边缘 | 边缘保持 |
| Test 6 | 中心峰值 | 中心高点 | 平滑效果 |
| Test 7 | 小图像 | 16x16 | 边界处理 |

### 1.3 当前测试平台优点

1. **覆盖基本功能场景**
2. **模块化测试函数设计**
3. **可配置的测试参数**
4. **输出统计信息**

### 1.4 当前测试平台不足

| 不足项 | 影响 | 严重程度 |
|--------|------|----------|
| 缺少预期输出验证 | 无法自动判断正确性 | 高 |
| 边界测试不充分 | 边界条件可能漏测 | 中 |
| 无中间结果检查 | 难以定位问题 | 中 |
| 缺少参数配置测试 | 配置组合未覆盖 | 中 |
| 无除零保护验证 | 极端情况未测试 | 高 |
| 缺少覆盖率收集 | 无法量化验证完整性 | 低 |

---

## 2. 增强建议

### 2.1 添加预期输出验证

**建议代码:**

```cpp
// ============================================================
// Verify Output Against Expected
// ============================================================
int verify_output(pixel_u10_t *output, pixel_u10_t *expected,
                  int width, int height, int tolerance) {
    int errors = 0;
    int max_diff = 0;
    long long total_diff = 0;

    for (int i = 0; i < width * height; i++) {
        int diff = abs((int)output[i] - (int)expected[i]);
        total_diff += diff;
        if (diff > max_diff) max_diff = diff;

        if (diff > tolerance) {
            errors++;
            if (errors <= 10) {  // Print first 10 errors
                int row = i / width;
                int col = i % width;
                std::cout << "  Error at (" << row << "," << col << "): "
                          << "expected=" << expected[i]
                          << ", actual=" << output[i]
                          << ", diff=" << diff << std::endl;
            }
        }
    }

    double avg_diff = (double)total_diff / (width * height);
    std::cout << "  Verification Results:" << std::endl;
    std::cout << "    Max difference: " << max_diff << std::endl;
    std::cout << "    Avg difference: " << avg_diff << std::endl;
    std::cout << "    Errors (tolerance=" << tolerance << "): " << errors << std::endl;

    return errors;
}
```

### 2.2 增强边界测试

**新增测试用例:**

```cpp
// ============================================================
// Test: Extreme Values (0 and 1023)
// ============================================================
void generate_extreme_image(pixel_u10_t *image, int width, int height, int value) {
    for (int i = 0; i < width * height; i++) {
        image[i] = value;
    }
}

// ============================================================
// Test: Gradient Zero Region
// ============================================================
void generate_zero_gradient_region(pixel_u10_t *image, int width, int height) {
    // Create image with flat region in center
    for (int row = 0; row < height; row++) {
        for (int col = 0; col < width; col++) {
            int idx = row * width + col;
            // Flat center
            if (row >= height/4 && row < 3*height/4 &&
                col >= width/4 && col < 3*width/4) {
                image[idx] = 512;
            } else {
                // Graduated edges
                image[idx] = (row < height/4) ? 256 : 768;
            }
        }
    }
}

// ============================================================
// Test: Corner Pixels
// ============================================================
void generate_corner_test_image(pixel_u10_t *image, int width, int height) {
    // Fill with middle value
    for (int i = 0; i < width * height; i++) {
        image[i] = 512;
    }
    // Mark corners with distinct values
    image[0] = 100;                    // Top-left
    image[width-1] = 200;              // Top-right
    image[(height-1)*width] = 300;     // Bottom-left
    image[height*width-1] = 400;       // Bottom-right
}
```

### 2.3 添加中间结果验证

**建议代码:**

```cpp
// ============================================================
// Stage-level Verification Structure
// ============================================================
struct stage_debug_t {
    bool enable;
    grad_t grad;
    win_size_t win_size;
    avg_value_t avg0_values[5];  // c, u, d, l, r
    avg_value_t avg1_values[5];
    blend_grad_t blend0_grad;
    blend_grad_t blend1_grad;
};

// ============================================================
// Verify Stage 1 Output
// ============================================================
int verify_stage1_output(grad_t actual_grad, win_size_t actual_win_size,
                         int expected_grad, int expected_win_size,
                         int tolerance) {
    int errors = 0;

    int grad_diff = abs((int)actual_grad - expected_grad);
    if (grad_diff > tolerance) {
        std::cout << "  Stage 1 gradient error: expected=" << expected_grad
                  << ", actual=" << actual_grad << std::endl;
        errors++;
    }

    if (actual_win_size != expected_win_size) {
        std::cout << "  Stage 1 win_size error: expected=" << expected_win_size
                  << ", actual=" << actual_win_size << std::endl;
        errors++;
    }

    return errors;
}
```

### 2.4 添加参数配置测试

**建议代码:**

```cpp
// ============================================================
// Test: Parameter Configuration Variations
// ============================================================
int run_parameter_test(int width, int height) {
    std::cout << "=== Parameter Configuration Test ===" << std::endl;

    int errors = 0;

    // Test different threshold configurations
    ap_uint<8> thresh_configs[3][4] = {
        {10, 20, 30, 40},  // Lower thresholds
        {16, 24, 32, 40},  // Default
        {20, 30, 40, 50},  // Higher thresholds
    };

    // Test different blend ratios
    ap_uint<8> ratio_configs[3][4] = {
        {16, 16, 16, 16},  // Low blend
        {32, 32, 32, 32},  // Default
        {48, 48, 48, 48},  // High blend
    };

    pixel_u10_t *input = new pixel_u10_t[width * height];
    pixel_u10_t *output = new pixel_u10_t[width * height];

    // Generate test input
    generate_test_image(input, width, height, 5);  // Random pattern

    for (int t = 0; t < 3; t++) {
        for (int r = 0; r < 3; r++) {
            // Run test with different configurations
            // ... call isp_csiir_top with different parameters
            std::cout << "Config: thresh=" << t << ", ratio=" << r
                      << ", output_mean=" << compute_mean(output, width*height)
                      << std::endl;
        }
    }

    delete[] input;
    delete[] output;
    return errors;
}
```

### 2.5 添加除零保护测试

**建议代码:**

```cpp
// ============================================================
// Test: Division by Zero Protection
// ============================================================
int test_division_protection() {
    std::cout << "=== Division Protection Test ===" << std::endl;
    int errors = 0;

    // Test div_by_5
    for (int x = 0; x <= 5115; x++) {
        ap_uint<13> input = x;
        ap_uint<11> result = div_by_5(input);
        int expected = x / 5;
        int error = abs((int)result - expected);
        if (error > 1) {
            std::cout << "  div_by_5(" << x << ") = " << result
                      << ", expected ~" << expected << std::endl;
            errors++;
        }
    }

    // Test div_by_lookup
    for (int num = -1000; num <= 1000; num++) {
        for (int den = 1; den <= 64; den++) {
            ap_int<16> n = num;
            ap_uint<7> d = den;
            ap_int<11> result = div_by_lookup(n, d);
            int expected = num / den;
            int error = abs((int)result - expected);
            if (error > 5) {
                std::cout << "  div_by_lookup(" << num << "," << den << ") = "
                          << result << ", expected " << expected << std::endl;
                errors++;
            }
        }
    }

    std::cout << "  Division protection test: " << (errors ? "FAIL" : "PASS") << std::endl;
    return errors;
}
```

### 2.6 添加覆盖率收集

**建议代码:**

```cpp
// ============================================================
// Coverage Collection Structure
// ============================================================
struct coverage_t {
    // Functional coverage
    int grad_ranges[5];      // 0-15, 16-23, 24-31, 32-39, 40+
    int win_sizes[5];        // 16, 23, 31, 39, 40
    int directions[5];       // c, u, d, l, r dominant
    int output_ranges[5];    // 0-255, 256-511, 512-767, 768-1023, overflow

    // Boundary coverage
    int first_row_pixels;
    int last_row_pixels;
    int first_col_pixels;
    int last_col_pixels;
    int corner_pixels;

    void reset() {
        for (int i = 0; i < 5; i++) {
            grad_ranges[i] = 0;
            win_sizes[i] = 0;
            directions[i] = 0;
            output_ranges[i] = 0;
        }
        first_row_pixels = 0;
        last_row_pixels = 0;
        first_col_pixels = 0;
        last_col_pixels = 0;
        corner_pixels = 0;
    }

    void update(grad_t grad, win_size_t win_size, pixel_u10_t output,
                int row, int col, int height, int width) {
        // Update gradient coverage
        if (grad <= 15) grad_ranges[0]++;
        else if (grad <= 23) grad_ranges[1]++;
        else if (grad <= 31) grad_ranges[2]++;
        else if (grad <= 39) grad_ranges[3]++;
        else grad_ranges[4]++;

        // Update window size coverage
        // ...

        // Update boundary coverage
        if (row == 0) first_row_pixels++;
        if (row == height - 1) last_row_pixels++;
        if (col == 0) first_col_pixels++;
        if (col == width - 1) last_col_pixels++;
        if ((row == 0 || row == height - 1) &&
            (col == 0 || col == width - 1)) corner_pixels++;
    }

    void report() {
        std::cout << "=== Coverage Report ===" << std::endl;
        std::cout << "Gradient ranges:" << std::endl;
        for (int i = 0; i < 5; i++) {
            std::cout << "  Range " << i << ": " << grad_ranges[i] << std::endl;
        }
        std::cout << "Boundary coverage:" << std::endl;
        std::cout << "  First row: " << first_row_pixels << std::endl;
        std::cout << "  Last row: " << last_row_pixels << std::endl;
        std::cout << "  First col: " << first_col_pixels << std::endl;
        std::cout << "  Last col: " << last_col_pixels << std::endl;
        std::cout << "  Corners: " << corner_pixels << std::endl;
    }
};
```

---

## 3. 建议的增强测试用例

### 3.1 新增测试用例列表

| 编号 | 测试项 | 描述 | 优先级 |
|------|--------|------|--------|
| TC-001 | 极值输入测试 | 全 0 和全 1023 输入 | 高 |
| TC-002 | 边界镜像验证 | 四边和四角像素处理 | 高 |
| TC-003 | 除零保护测试 | 梯度为 0 区域 | 高 |
| TC-004 | 参数组合测试 | 不同配置参数组合 | 中 |
| TC-005 | 连续帧测试 | 多帧处理正确性 | 中 |
| TC-006 | 背压测试 | TREADY 反压情况 | 中 |
| TC-007 | 吞吐量测试 | 连续像素处理 | 中 |
| TC-008 | 中间结果验证 | 各阶段输出正确性 | 低 |

### 3.2 测试用例详细描述

#### TC-001: 极值输入测试

**目的:** 验证输入为 0 和 1023 时输出正确限幅。

**测试步骤:**
1. 输入全 0 图像
2. 验证输出非负且合理
3. 输入全 1023 图像
4. 验证输出不超过 1023

**预期结果:**
- 全 0 输入 -> 输出接近 0
- 全 1023 输入 -> 输出接近 1023

#### TC-002: 边界镜像验证

**目的:** 验证边界像素处理正确。

**测试步骤:**
1. 创建角落标记图像
2. 处理并验证角落输出
3. 检查边界像素梯度值

**预期结果:**
- 边界像素正确使用镜像值

---

## 4. 实施建议

### 4.1 优先级排序

| 优先级 | 增强项 | 工作量 | 影响 |
|--------|--------|--------|------|
| P1 | 预期输出验证 | 低 | 高 |
| P1 | 除零保护测试 | 低 | 高 |
| P1 | 极值输入测试 | 低 | 高 |
| P2 | 边界测试增强 | 中 | 中 |
| P2 | 参数配置测试 | 中 | 中 |
| P3 | 中间结果验证 | 高 | 中 |
| P3 | 覆盖率收集 | 高 | 低 |

### 4.2 实施步骤

1. **阶段 1 (立即):**
   - 添加预期输出验证函数
   - 添加极值输入测试
   - 添加除零保护测试

2. **阶段 2 (短期):**
   - 增强边界测试用例
   - 添加参数配置测试
   - 集成外部测试向量

3. **阶段 3 (长期):**
   - 添加中间结果验证
   - 实现覆盖率收集
   - 自动化回归测试

---

## 5. 完整增强测试平台示例

```cpp
// tb_isp_csiir_enhanced.cpp
// ISP-CSIIR Enhanced Test Bench

#include <iostream>
#include <fstream>
#include <cmath>
#include <cstdlib>
#include "isp_csiir.h"

// Test configuration
#define TEST_WIDTH      64
#define TEST_HEIGHT     64
#define TOLERANCE       2

// Forward declarations
int verify_output(pixel_u10_t *output, pixel_u10_t *expected,
                  int width, int height, int tolerance);
int test_extreme_values();
int test_boundary_conditions();
int test_division_protection();
int test_parameter_variations();

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "ISP-CSIIR Enhanced Test Bench" << std::endl;
    std::cout << "========================================" << std::endl;

    int total_errors = 0;

    // Run enhanced tests
    total_errors += test_extreme_values();
    total_errors += test_boundary_conditions();
    total_errors += test_division_protection();
    total_errors += test_parameter_variations();

    // Summary
    std::cout << "\n========================================" << std::endl;
    std::cout << "Test Summary:" << std::endl;
    std::cout << "  Total errors: " << total_errors << std::endl;
    std::cout << "========================================" << std::endl;

    return (total_errors == 0) ? 0 : 1;
}
```

---

## 6. 结论

现有测试平台提供了基本的功能覆盖，但建议增加以下关键增强：

1. **预期输出验证** - 实现自动化结果验证
2. **边界条件测试** - 确保边界处理正确
3. **除零保护测试** - 验证极端情况处理
4. **参数配置测试** - 覆盖不同配置组合

这些增强将显著提高验证完整性和自动化程度。

---

## 修订历史

| 版本 | 日期 | 作者 | 描述 |
|------|------|------|------|
| v1.0 | 2026-03-23 | rtl-verf | 初始版本 |
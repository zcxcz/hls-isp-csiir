# ISP-CSIIR HLS 架构设计文档

## 文档信息

| 项目 | 内容 |
|------|------|
| 项目名称 | ISP-CSIIR HLS 模块 |
| 项目编号 | prj_0 |
| 文档版本 | v1.0 |
| 创建日期 | 2026-03-23 |
| 作者 | rtl-arch |
| 状态 | 待评审 |

---

## 1. 系统架构概述

### 1.1 设计目标

| 参数 | 目标值 |
|------|--------|
| 目标频率 | 600 MHz |
| 工艺节点 | 12nm |
| 吞吐量 | 1 pixel/clock (II=1) |
| 数据位宽 | 10-bit 无符号输入/输出 |

### 1.2 HLS 设计方法

本设计采用 High-Level Synthesis (HLS) 方法实现，具有以下特点：

- **源语言**: C++ (Vitis HLS 兼容)
- **目标输出**: Verilog-2001 可综合 RTL
- **流水线策略**: 细粒度流水线 (PIPELINE II=1)
- **接口类型**: AXI-Stream (数据) + AXI-Lite (配置)

### 1.3 系统架构框图

```
                         AXI-Stream Input
                              |
                              v
                    +-------------------+
                    |   Line Buffer     |  <-- 4行缓存
                    |   Controller      |
                    +-------------------+
                              |
                              v
                    +-------------------+
                    |   Stage 1         |  梯度计算
                    |   Gradient        |  + 窗口大小确定
                    +-------------------+
                              |
                              v
                    +-------------------+
                    |   Stage 2         |  多尺度
                    |   Average         |  方向性平均
                    +-------------------+
                              |
                              v
                    +-------------------+
                    |   Stage 3         |  梯度加权
                    |   Blend           |  方向融合
                    +-------------------+
                              |
                              v
                    +-------------------+
                    |   Stage 4         |  IIR滤波
                    |   Output          |  + 混合输出
                    +-------------------+
                              |
                              v
                         AXI-Stream Output
```

---

## 2. 模块层次结构

### 2.1 顶层模块结构

```
isp_csiir_top
├── line_buffer_inst      // 行缓存模块
├── stage1_gradient       // 梯度计算模块
├── stage2_average        // 方向性平均模块
├── stage3_blend          // 梯度融合模块
└── stage4_output         // 输出模块
```

### 2.2 HLS 模块接口

```cpp
void isp_csiir_top(
    // AXI-Stream 数据输入
    hls::stream<pixel_u10_t> &din_stream,
    // AXI-Stream 数据输出
    hls::stream<pixel_u10_t> &dout_stream,
    // 配置参数
    ap_uint<16> img_width,
    ap_uint<16> img_height,
    ap_uint<8>  win_thresh[4],
    ap_uint<8>  grad_clip[4],
    ap_uint<8>  blend_ratio[4],
    // 控制
    ap_uint<1>  &ap_start,
    ap_uint<1>  &ap_done,
    ap_uint<1>  &ap_idle,
    ap_uint<1>  &ap_ready
);
```

---

## 3. 行缓存架构

### 3.1 缓存需求分析

**5x5 窗口需要 5 行数据**，当前行位于中心时需要：
- 当前行的前 2 行
- 当前行
- 当前行的后 2 行

**行缓存设计：**
- 使用 **4 行缓存** 存储历史行数据
- 第 5 行为当前输入行

### 3.2 行缓存结构

```
输入像素流
    |
    v
+--------+    +--------+    +--------+    +--------+
| Line 0 | -> | Line 1 | -> | Line 2 | -> | Line 3 |
+--------+    +--------+    +--------+    +--------+
    |             |             |             |
    +-------+-----+-----+-------+             |
            |     |     |                     |
            v     v     v                     v
          win[0] win[1] win[2]             win[3]  <- 窗口列缓存
            |     |     |                     |
            +-----+-----+-----+-----+---------+
                  |     |     |     |
                  v     v     v     v     v
               win[0] win[1] win[2] win[3] win[4]  <- 5x5窗口输出
```

### 3.3 HLS 行缓存实现

```cpp
// 行缓存 + 窗口缓存
void line_buffer_window(
    hls::stream<pixel_u10_t> &din,
    pixel_u10_t window[5][5],
    ap_uint<16> col_count
) {
    // 4 行缓存 (每行最大 8192 像素)
    static pixel_u10_t line_buf[4][MAX_WIDTH];
    #pragma HLS ARRAY_PARTITION variable=line_buf dim=1 complete
    #pragma HLS RESOURCE variable=line_buf core=RAM_2P_BRAM

    // 列缓存 (5 列)
    static pixel_u10_t col_buf[5][4];
    #pragma HLS ARRAY_PARTITION variable=col_buf complete

    // 行缓存移位和更新
    // ... 具体实现见 HLS 代码
}
```

### 3.4 行缓存资源估算

| 组件 | 容量 | BRAM 数量 |
|------|------|-----------|
| Line Buffer (4行) | 4 × 8192 × 10-bit | 8 BRAM (18K) |
| Column Buffer | 5 × 4 × 10-bit | 寄存器实现 |
| Gradient Buffer (3行) | 3 × 8192 × 16-bit | 6 BRAM (18K) |

### 3.5 设计决策：avg_u 不需要行缓冲

**背景**：在 Stage 4 输出阶段，`avg_u` 和 `avg1_u` 表示"上方向"的平均值。

**关键洞察**：`avg_u` 是**空间概念**，而非时间序列概念。

```
avg_u = 上方向平均值 (空间上的"上")

计算方式：在当前像素的 5x5 窗口内
    avg_u = Σ window[row-1][col]  (窗口内上方行的像素平均)

这说明：
- avg_u 来自于 Line Buffer 已经缓存的上方行数据
- 不需要额外的行间递归存储
- 不需要 avg_u_delay 延迟线
```

**决策**：

| 原设计（冗余） | 优化后设计 |
|----------------|------------|
| avg_u_delay: 2 行 BRAM | 移除 |
| 用于存储上一行的 avg_u 值 | 不需要（avg_u 是空间计算） |

**原因分析**：

1. **avg_u 是空间定义**：在 `stage2_average()` 中，avg_u 表示当前窗口内"上"方向邻域的平均值，而非"上一行像素的平均值"

2. **Line Buffer 已提供数据**：Line Buffer 已经缓存了 4 行历史数据，可以即时计算当前窗口内任意行的平均值

3. **无递归依赖**：Stage 4 的 `stage4_output()` 函数中，`avg0_u` 和 `avg1_u` 直接作为空间参数参与融合计算，没有时间序列依赖

### 3.6 最终 Line Buffer 资源统计

| 缓存类型 | 行数 | 位宽 | 容量 | BRAM (18K) |
|----------|------|------|------|------------|
| Line Buffer | 4 行 | 10-bit | 4 × 8192 × 10 | 8 |
| Gradient Buffer | 3 行 | 16-bit | 3 × 8192 × 16 | 6 |
| **总计** | - | - | - | **14 BRAM** |

**优化节省**：移除 avg_u_delay 后，节省约 **4 BRAM**（假设 2 行 × 2 尺度 × 10-bit）

---

## 4. 流水线架构

### 4.1 HLS 流水线策略

**目标：II=1 (每周期处理 1 像素)**

```
时钟周期:   | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | ...
------------+---+---+---+---+---+---+---+---+----
像素输入:   | P0| P1| P2| P3| P4| P5| P6| P7| ...
            |
Line Buffer | P0| P1| P2| P3| P4| P5| P6| P7| ...
Delay (2行) |   |   |   |...|   |   |   |   |
            |       [填充延迟 ~2行周期]
            |                       | P0| P1| P2| ...
Stage 1     |                       |grad|win |...
Stage 2     |                       | avg_values |
Stage 3     |                       | blend_grad |
Stage 4     |                       | output     |
            |                                   | P0|...
输出:       |                                   | R0| R1| R2| ...
```

### 4.2 DATAFLOW 架构

```cpp
void isp_csiir_top(...) {
    #pragma HLS DATAFLOW

    // 内部流
    hls::stream<pixel_u10_t> lb_out_stream;
    hls::stream<grad_t> grad_stream;
    hls::stream<win_size_t> win_size_stream;
    hls::stream<avg_values_t> avg_stream;
    hls::stream<blend_grad_t> blend_stream;

    #pragma HLS STREAM variable=lb_out_stream depth=64
    #pragma HLS STREAM variable=grad_stream depth=32
    // ...

    // 级联处理
    line_buffer_stage(din_stream, lb_out_stream, ...);
    stage1_gradient(lb_out_stream, grad_stream, win_size_stream, ...);
    stage2_average(lb_out_stream, win_size_stream, avg_stream, ...);
    stage3_blend(grad_stream, avg_stream, blend_stream, ...);
    stage4_output(blend_stream, dout_stream, ...);
}
```

### 4.3 各阶段流水级数估算

| 阶段 | 主要运算 | 估算流水级数 |
|------|----------|--------------|
| Line Buffer | 移位 + 更新 | 1-2 |
| Stage 1 | Sobel卷积 + 除法近似 + LUT | 4-6 |
| Stage 2 | 加权平均 + 除法 | 6-10 |
| Stage 3 | 排序 + 加权融合 + 除法 | 8-12 |
| Stage 4 | 水平混合 + 窗混合 + 输出 | 4-6 |
| **总延迟** | - | **25-40 cycles + 2行延迟** |

---

## 5. 除法器架构

### 5.1 除法操作分类

| 除法类型 | 场景 | 方案 |
|----------|------|------|
| **常数除法** | grad/5, /64 | 乘法近似或移位 |
| **变量除法(小范围)** | avg/sum_factor | 倒数查表 |
| **变量除法(大范围)** | blend/grad_sum | NR迭代 |

### 5.2 常数除法实现

#### grad/5 乘法近似

```cpp
// grad/5 ≈ (grad * 205) >> 10
ap_uint<12> div_by_5(ap_uint<13> grad_abs) {
    #pragma HLS PIPELINE II=1
    ap_uint<23> product = grad_abs * 205;
    ap_uint<12> result = product >> 10;
    return result;
}
```

#### /64 移位实现

```cpp
// x/64 = x >> 6
ap_int<11> div_by_64(ap_int<17> x) {
    #pragma HLS PIPELINE II=1
    return x >> 6;
}
```

### 5.3 变量除法实现

#### avg_value 除法 (倒数查表)

sum_factor 只有 8 个可能值：{1, 6, 9, 10, 15, 16, 25, 40, 64}

```cpp
// 倒数查表 (定点 2^16)
const ap_uint<16> inv_table[65] = {
    // 0: unused
    // 1: 65536
    0, 65536, 32768, 21845, 16384, 13107, 10923, 9362, 8192, 7282,
    6554, 5958, 5461, 5041, 4681, 4369, 4096, 3855, 3641, 3449,
    3277, 3121, 2979, 2849, 2731, 2621, 2521, 2427, 2341, 2250,
    2185, 2115, 2048, 1986, 1928, 1872, 1820, 1771, 1725, 1680,
    1638, 1598, 1560, 1524, 1490, 1457, 1425, 1395, 1365, 1337,
    1311, 1285, 1260, 1237, 1214, 1192, 1170, 1150, 1130, 1111,
    1092, 1074, 1057, 1040, 1024
};

ap_int<11> div_by_lookup(ap_int<16> num, ap_uint<7> den) {
    #pragma HLS PIPELINE II=1
    ap_uint<16> inv = inv_table[den];
    ap_int<32> product = num * inv;
    // 负数处理
    ap_int<32> result = (num >= 0) ? (product >> 16) : -((-product) >> 16);
    return result.range(10, 0);
}
```

#### blend_grad 除法 (Newton-Raphson迭代)

```cpp
// Newton-Raphson 迭代求倒数
// x_0 = initial_guess(1/D)
// x_1 = x_0 * (2 - D * x_0)
// x_2 = x_1 * (2 - D * x_1)
// Q = N * x_2

ap_int<11> div_by_nr(ap_int<23> num, ap_uint<14> den) {
    #pragma HLS PIPELINE II=1

    // 初始估计 (查表或移位)
    ap_uint<16> x0 = initial_reciprocal(den);

    // NR 迭代 1
    ap_uint<30> prod0 = den * x0;
    ap_int<30> two_minus = (2 << 16) - prod0;
    ap_uint<16> x1 = (x0 * two_minus) >> 16;

    // NR 迭代 2 (可选，更高精度)
    ap_uint<30> prod1 = den * x1;
    ap_int<30> two_minus2 = (2 << 16) - prod1;
    ap_uint<16> x2 = (x1 * two_minus2) >> 16;

    // 计算商
    ap_int<40> quotient = (num * x2) >> 16;
    return quotient.range(10, 0);
}
```

### 5.4 除法器资源与时序

| 除法类型 | DSP48 | Latency | 600MHz 可行性 |
|----------|-------|---------|---------------|
| 乘法近似 (/5) | 1 | 1 | ✓ 确认可行 |
| 移位 (/64) | 0 | 1 | ✓ 无问题 |
| 倒数查表 | 1 | 1 | ✓ 确认可行 |
| NR迭代(2次) | 4 | 4-6 | ✓ 需流水化 |

---

## 6. HLS 优化策略

### 6.1 Pragma 使用指南

```cpp
// 主函数
void isp_csiir_top(...) {
    // 接口定义
    #pragma HLS INTERFACE axis port=din_stream
    #pragma HLS INTERFACE axis port=dout_stream
    #pragma HLS INTERFACE s_axilite port=img_width
    #pragma HLS INTERFACE s_axilite port=img_height
    #pragma HLS INTERFACE ap_ctrl_hs port=return

    // 数据流架构
    #pragma HLS DATAFLOW
}

// 处理循环
void process_loop(...) {
    for (int i = 0; i < total_pixels; i++) {
        #pragma HLS PIPELINE II=1 rewind

        // 处理逻辑
    }
}

// 数组分区
pixel_u10_t window[5][5];
#pragma HLS ARRAY_PARTITION variable=window complete

// 内联小函数
#pragma HLS INLINE
```

### 6.2 关键优化点

| 优化项 | Pragma | 目的 |
|--------|--------|------|
| 主循环流水化 | PIPELINE II=1 | 达到每周期 1 像素吞吐量 |
| 数组完全分区 | ARRAY_PARTITION complete | 消除存储访问瓶颈 |
| 函数内联 | INLINE | 减少函数调用开销 |
| 流深设置 | STREAM depth=N | 避免 DATAFLOW 死锁 |
| 资源绑定 | RESOURCE core=RAM_2P_BRAM | 指定存储类型 |

### 6.3 II=1 实现关键

**确保 II=1 的关键点：**

1. **避免循环依赖**
   ```cpp
   // 错误：存在依赖
   for (int i = 1; i < N; i++) {
       sum += arr[i] - arr[i-1];  // arr[i-1] 依赖上一轮
   }

   // 正确：移除依赖
   prev = arr[0];
   for (int i = 1; i < N; i++) {
       #pragma HLS PIPELINE II=1
       curr = arr[i];
       sum += curr - prev;
       prev = curr;
   }
   ```

2. **避免条件分支导致的资源冲突**
   ```cpp
   // 使用条件赋值替代 if-else
   result = (condition) ? value_a : value_b;
   ```

3. **数组访问模式优化**
   ```cpp
   // 分区数组以支持并行访问
   #pragma HLS ARRAY_PARTITION variable=data cyclic factor=4
   ```

---

## 7. 时序分析

### 7.1 关键路径分析

| 阶段 | 关键运算 | 组合逻辑深度 | 600MHz 可行性 |
|------|----------|--------------|---------------|
| S1 | Sobel卷积求和 | ~8 FO4 | ✓ |
| S1 | 乘法近似 | ~12 FO4 | ✓ |
| S2 | 加权求和 | ~10 FO4 | ✓ |
| S2 | 倒数查表乘法 | ~12 FO4 | ✓ |
| S3 | 排序网络 | ~15 FO4 | ✓ |
| S3 | NR迭代乘法 | ~12 FO4 | ✓ |
| S4 | 混合乘法 | ~10 FO4 | ✓ |

### 7.2 12nm 工艺参考

| 参数 | 参考值 |
|------|--------|
| FO4 延迟 | ~20ps |
| 单级逻辑深度预算 | < 20 FO4 (600MHz) |
| DSP48 延迟 | ~2ns (可流水化) |
| BRAM 延迟 | ~1.5ns |

### 7.3 时序风险点

| 风险点 | 缓解措施 |
|--------|----------|
| NR迭代乘法链 | 插入流水寄存器 |
| 排序网络 | 使用部分流水化 |
| 行缓存读取 | 使用双口BRAM |

---

## 8. 资源估算

### 8.1 存储资源

| 组件 | 容量 | BRAM (18K) |
|------|------|------------|
| Line Buffer (4行) | 4 × 8192 × 10-bit | 8 |
| Gradient Buffer (3行) | 3 × 8192 × 16-bit | 6 |
| 配置寄存器 | ~128 bits | 0 (FF) |
| LUT系数 | ~1KB | 1 |
| **总计** | - | **~15 BRAM** |

> **优化说明**：原设计中包含 avg_u_delay（2 行 BRAM，约 4 BRAM），用于存储上一行的上方向平均值。经分析，avg_u 是空间概念（窗口内上方邻域的平均值），而非时间序列概念，不需要行间递归存储。移除后节省约 **4 BRAM**。

### 8.2 计算资源

| 运算类型 | 数量 | DSP48 估算 |
|----------|------|------------|
| 乘法 (卷积) | 25 × 2 (Sobel) | 2 |
| 乘法 (加权) | ~20 | 10 |
| 除法 (查表) | ~10 | 5 |
| 除法 (NR) | 2 | 8 |
| 排序比较 | 10 | 0 (LUT) |
| **总计** | - | **~25 DSP** |

### 8.3 逻辑资源

| 组件 | LUT 估算 | FF 估算 |
|------|----------|---------|
| 控制逻辑 | ~500 | ~200 |
| 数据通路 | ~5000 | ~3000 |
| 排序网络 | ~300 | ~100 |
| 行缓存控制 | ~200 | ~100 |
| **总计** | **~6000** | **~3400** |

---

## 9. 边界处理设计

### 9.1 图像边界处理

```cpp
// 梯度边界处理
grad_t get_grad_with_boundary(
    grad_t grad_center[5][5],
    int row, int col,
    int img_height, int img_width
) {
    #pragma HLS INLINE

    // 边界镜像处理
    int row_u = (row == 0) ? row : row - 1;
    int row_d = (row == img_height - 1) ? row : row + 1;
    int col_l = (col == 0) ? col : col - 1;
    int col_r = (col == img_width - 1) ? col : col + 1;

    // 返回对应梯度
    // ...
}
```

### 9.2 滤波窗边界处理

```cpp
// 边界复制
pixel_u10_t get_pixel_boundary(
    pixel_u10_t img[][MAX_WIDTH],
    int row, int col,
    int max_row, int max_col
) {
    #pragma HLS INLINE

    int r = (row < 0) ? 0 : (row > max_row) ? max_row : row;
    int c = (col < 0) ? 0 : (col > max_col) ? max_col : col;
    return img[r][c];
}
```

---

## 10. 验证策略

### 10.1 C 仿真验证

```cpp
// 测试平台
int main() {
    hls::stream<pixel_u10_t> din;
    hls::stream<pixel_u10_t> dout;

    // 加载测试图像
    load_test_image(din, "test_image.txt");

    // 运行设计
    isp_csiir_top(din, dout, ...);

    // 验证输出
    verify_output(dout, "expected_output.txt");

    return 0;
}
```

### 10.2 关键测试场景

| 测试场景 | 目的 |
|----------|------|
| 边界像素 | 验证边界处理正确性 |
| 高梯度区域 | 验证窗口大小选择 |
| 低梯度区域 | 验证平滑效果 |
| 极值输入 | 验证溢出处理 |
| 连续帧 | 验证状态重置 |

---

## 11. 风险与待确认事项

### 11.1 技术风险

| 风险项 | 风险等级 | 缓解措施 |
|--------|----------|----------|
| 600MHz 时序收敛 | 中 | 流水化关键路径 |
| NR迭代精度 | 低 | 增加迭代次数 |
| 行缓存延迟 | 低 | 明确延迟规格 |

### 11.2 待确认事项

| 编号 | 事项 | 决策方 |
|------|------|--------|
| 1 | HLS工具版本确认 | 用户 |
| 2 | 目标平台确认 (FPGA/ASIC) | 用户 |
| 3 | 资源预算确认 | 用户 |
| 4 | 行缓存延迟容忍度 | 系统级 |

---

## 修订历史

| 版本 | 日期 | 作者 | 描述 |
|------|------|------|------|
| v1.1 | 2026-03-24 | rtl-arch | 更新 Line Buffer 优化决策：移除 avg_u_delay，说明 avg_u 空间概念，更新资源估算 |
| v1.0 | 2026-03-23 | rtl-arch | 初始版本 |